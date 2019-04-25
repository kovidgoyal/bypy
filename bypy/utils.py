#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


import atexit
import ctypes
import errno
import fcntl
import glob
import os
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import time
import zipfile
from contextlib import contextmanager
from functools import partial

from .constants import (LIBDIR, MAKEOPTS, PATCHES, PREFIX, PYTHON, build_dir,
                        islinux, iswindows, mkdtemp, worker_env)

if iswindows:
    import msvcrt
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    get_file_type = k32.GetFileType
    get_file_type.argtypes = [wintypes.HANDLE]
    get_file_type.restype = wintypes.DWORD
    get_file_info_by_handle = k32.GetFileInformationByHandleEx
    get_file_info_by_handle.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    get_file_info_by_handle.restype = wintypes.BOOL

    def rmtree(x, tries=10):
        for i in range(tries):
            try:
                return shutil.rmtree(x)
            except WindowsError as err:
                if i >= tries - 1:
                    raise
                if err.winerror == 32:
                    # sharing violation (file open in another process)
                    time.sleep(1)
                    continue
                raise

    def split(x):
        x = x.replace('\\', '\\\\')
        return shlex.split(x)
else:
    rmtree = shutil.rmtree
    split = shlex.split


hardlink = os.link
ensure_dir = partial(os.makedirs, exist_ok=True)


def print_cmd(cmd):
    print('\033[92m', end='')
    print(*cmd, end='\033[0m\n')


def call(*cmd, echo=True):
    if len(cmd) == 1 and isinstance(cmd[0], str):
        cmd = shlex.split(cmd[0])
    if echo:
        print_cmd(cmd)
    ret = subprocess.Popen(cmd).wait()
    if ret != 0:
        print('The failing command was:')
        print_cmd(cmd)
        raise SystemExit(ret)


def single_instance(name):
    address = '\0' + name.replace(' ', '_')
    sock = socket.socket(family=socket.AF_UNIX)
    try:
        sock.bind(address)
    except socket.error as err:
        if getattr(err, 'errno', None) == errno.EADDRINUSE:
            return False
        raise
    fd = sock.fileno()
    old_flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    fcntl.fcntl(fd, fcntl.F_SETFD, old_flags | fcntl.FD_CLOEXEC)
    atexit.register(sock.close)
    return True


def current_env(library_path=False):
    env = os.environ.copy()
    env.update(worker_env)
    if library_path:
        if library_path is True:
            library_path = LIBDIR
        else:
            library_path = library_path + os.pathsep + LIBDIR
        env['LD_LIBRARY_PATH'] = library_path
    return env


def isatty():
    if isatty.no_tty:
        return False
    f = sys.stdout
    if f.isatty():
        return True
    if not iswindows:
        return False
    # Check for a cygwin ssh pipe
    buf = ctypes.create_string_buffer(1024)
    h = msvcrt.get_osfhandle(f.fileno())
    if get_file_type(h) != 3:
        return False
    ret = get_file_info_by_handle(h, 2, buf, ctypes.sizeof(buf))
    if not ret:
        raise ctypes.WinError()
    data = buf.raw
    name = data[4:].decode('utf-16').rstrip(u'\0')
    parts = name.split('-')
    return (
        parts[0] == r'\cygwin' and parts[2].startswith('pty') and
        parts[4] == 'master')


isatty.no_tty = False


def set_title(x):
    if isatty():
        print('''\033]2;%s\007''' % x)


def run_shell(library_path=False):
    if not isatty():
        raise SystemExit('STDOUT is not a tty, aborting...')
    sh = 'C:/cygwin64/bin/zsh' if iswindows else '/bin/zsh'
    env = current_env(library_path=library_path)
    if iswindows:
        from .constants import cygwin_paths
        paths = env['PATH'].split(os.pathsep)
        paths = cygwin_paths + paths
        env['PATH'] = os.pathsep.join(paths)
    return subprocess.Popen([sh, '-i'], env=env).wait()


def run(*args, **kw):
    if len(args) == 1 and isinstance(args[0], str):
        cmd = split(args[0])
    else:
        cmd = args
    print(' '.join(shlex.quote(x) for x in cmd))
    sys.stdout.flush()
    env = current_env(library_path=kw.get('library_path'))
    p = subprocess.Popen(cmd, env=env, cwd=kw.get('cwd'))
    rc = p.wait()
    if kw.get('no_check'):
        return rc
    if rc != 0:
        cmd = ' '.join(shlex.quote(x) for x in cmd)
        raise subprocess.CalledProcessError(rc, cmd)


def lcopy(src, dst, no_hardlinks=False):
    try:
        if os.path.islink(src):
            linkto = os.readlink(src)
            os.symlink(linkto, dst)
            return True
        else:
            if no_hardlinks:
                shutil.copy(src, dst)
            else:
                os.link(src, dst)
            return False
    except FileExistsError:
        os.unlink(dst)
        return lcopy(src, dst)


def ensure_clear_dir(path):
    if os.path.exists(path):
        rmtree(path)
    os.makedirs(path)


def extract(source):
    if source.lower().endswith('.zip'):
        with zipfile.ZipFile(source) as zf:
            zf.extractall()
    else:
        with tarfile.open(source, encoding='utf-8') as tf:
            tf.extractall()


def chdir_for_extract(name):
    tdir = mkdtemp(prefix=os.path.basename(name).split('-')[0] + '-')
    os.chdir(tdir)
    return tdir


def extract_source_and_chdir(source):
    tdir = chdir_for_extract(source)
    print('Extracting source:', source)
    sys.stdout.flush()
    extract(source)
    x = os.listdir('.')
    if len(x) == 1:
        os.chdir(x[0])
    return tdir


def simple_build(
        configure_args=(), make_args=(), install_args=(),
        library_path=None, override_prefix=None, no_parallel=False,
        configure_name='./configure'):
    if isinstance(configure_args, str):
        configure_args = split(configure_args)
    if isinstance(make_args, str):
        make_args = split(make_args)
    if isinstance(install_args, str):
        install_args = split(install_args)
    run(configure_name, '--prefix=' + (
        override_prefix or build_dir()), *configure_args)
    make_opts = [] if no_parallel else split(MAKEOPTS)
    run('make', *(make_opts + list(make_args)))
    mi = ['make'] + list(install_args) + ['install']
    run(*mi, library_path=library_path)


def is_macho_binary(p):
    try:
        with open(p, 'rb') as f:
            return f.read(4) in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf')
    except FileNotFoundError:
        return False


def read_lib_names(p):
    lines = subprocess.check_output(
            ['otool', '-D', p]).decode('utf-8').splitlines()
    install_name = None
    if len(lines) > 1:
        install_name = lines[1].strip()
    lines = subprocess.check_output(
            ['otool', '-L', p]).decode('utf-8').splitlines()
    deps = []
    for line in lines[1:]:
        val = line.partition('(')[0].strip()
        if val != install_name:
            deps.append(val)
    return install_name, deps


def flipwritable(fn, mode=None):
    """
    Flip the writability of a file and return the old mode. Returns None
    if the file is already writable.
    """
    if os.access(fn, os.W_OK):
        return None
    old_mode = os.stat(fn).st_mode
    os.chmod(fn, stat.S_IWRITE | old_mode)
    return old_mode


def change_lib_names(p, changes):
    cmd = ['install_name_tool']
    for old_name, new_name in changes:
        if old_name is None:
            cmd.extend(['-id', new_name])
        else:
            cmd.extend(['-change', old_name, new_name])
    cmd.append(p)
    old_mode = flipwritable(p)
    subprocess.check_call(cmd)
    if old_mode is not None:
        flipwritable(p, old_mode)


def fix_install_names(m, output_dir):
    dylibs = set()
    mfunc = getattr(m, 'install_name_change_predicate', lambda p: False)
    mcfunc = getattr(m, 'install_name_change',
                        lambda old_name, is_dep: old_name)
    for dirpath, dirnames, filenames in os.walk(output_dir):
        for f in filenames:
            p = os.path.abspath(os.path.realpath(os.path.join(dirpath, f)))
            if (
                p not in dylibs and
                os.path.exists(p) and
                (p.endswith('.dylib') or (
                    is_macho_binary(p) and (
                    'bin' in p.split('/') or mfunc(p))))
            ):
                dylibs.add(p)
    for p in dylibs:
        changes = []
        install_name, deps = read_lib_names(p)
        if install_name:
            nn = install_name.replace(output_dir, PREFIX)
            nn = mcfunc(nn, False)
            if nn != install_name:
                changes.append((None, nn))
        for name in deps:
            nn = name.replace(output_dir, PREFIX)
            nn = mcfunc(nn, True)
            if nn != name:
                changes.append((name, nn))
        if changes:
            print('Changing lib names in:', p)
            change_lib_names(p, changes)


def python_build(extra_args=()):
    if isinstance(extra_args, str):
        extra_args = split(extra_args)
    run(PYTHON, 'setup.py', 'install', '--root', build_dir(),
        *extra_args, library_path=True)


def create_package(module, src_dir, outpath):

    exclude = getattr(module, 'pkg_exclude_names', frozenset(
        'doc man info test tests gtk-doc README'.split()))
    exclude_extensions = getattr(module, 'pkg_exclude_extensions', frozenset((
        'pyc', 'pyo', 'la', 'chm', 'cpp', 'rst', 'md')))

    try:
        shutil.rmtree(outpath)
    except FileNotFoundError:
        pass

    os.makedirs(outpath)

    for dirpath, dirnames, filenames in os.walk(src_dir):

        def get_name(x):
            return os.path.relpath(os.path.join(dirpath, x),
                                   src_dir).replace(os.sep, '/')

        def is_ok(name):
            parts = name.split('/')
            for p in parts:
                if p in exclude or p.rpartition('.')[-1] in exclude_extensions:
                    return False
            if hasattr(module, 'filter_pkg') and module.filter_pkg(parts):
                return False
            return True

        for d in tuple(dirnames):
            if os.path.islink(os.path.join(dirpath, d)):
                dirnames.remove(d)
                filenames.append(d)
                continue
            name = get_name(d)
            if is_ok(name):
                try:
                    os.makedirs(os.path.join(outpath, name))
                except EnvironmentError as err:
                    if err.errno != errno.EEXIST:
                        raise
            else:
                dirnames.remove(d)

        for f in filenames:
            name = get_name(f)
            if is_ok(name):
                # on Linux hardlinking fails because the package is
                # built in tmpfs and outpath is on a different volume
                lcopy(os.path.join(dirpath, f), os.path.join(outpath, name),
                      no_hardlinks=islinux)


@contextmanager
def tempdir(prefix='tmp-'):
    tdir = mkdtemp(prefix)
    yield tdir
    rmtree(tdir)


def walk(path='.'):
    ''' A nice interface to os.walk '''
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            yield os.path.join(dirpath, f)


def copy_headers(pattern, destdir='include'):
    dest = os.path.join(build_dir(), destdir)
    ensure_dir(dest)
    files = glob.glob(pattern)
    for f in files:
        dst = os.path.join(dest, os.path.basename(f))
        if os.path.isdir(f):
            shutil.copytree(f, dst)
        else:
            shutil.copy2(f, dst)


def library_symlinks(full_name, destdir='lib'):
    parts = full_name.split('.')
    idx = parts.index('so')
    basename = '.'.join(parts[:idx + 1])
    parts = parts[idx + 1:]
    for i in range(len(parts)):
        suffix = '.'.join(parts[:i])
        if suffix:
            suffix = '.' + suffix
        ln = os.path.join(build_dir(), destdir, basename + suffix)
        try:
            os.symlink(full_name, ln)
        except FileExistsError:
            os.unlink(ln)
            os.symlink(full_name, ln)


def install_binaries(
    pattern, destdir='lib', do_symlinks=False, fname_map=os.path.basename
):
    dest = os.path.join(build_dir(), destdir)
    os.makedirs(dest, exist_ok=True)
    files = glob.glob(pattern)
    files.sort(key=len, reverse=True)
    if not files:
        raise ValueError(
            f'The pattern {pattern} did not match any actual files')
    for f in files:
        dst = os.path.join(dest, fname_map(f))
        islink = lcopy(f, dst)
        if not islink:
            os.chmod(dst, 0o755)
        if iswindows and os.path.exists(f + '.manifest'):
            shutil.copy(f + '.manifest', dst + '.manifest')
    if do_symlinks:
        library_symlinks(files[0], destdir=destdir)


def replace_in_file(path, old, new, missing_ok=False):
    if isinstance(old, str):
        old = old.encode('utf-8')
    if isinstance(new, str):
        new = new.encode('utf-8')
    with open(path, 'r+b') as f:
        raw = f.read()
        if isinstance(old, bytes):
            nraw = raw.replace(old, new)
        else:
            if isinstance(old.pattern, str):
                old = re.compile(old.pattern.encode('utf-8'), old.flags)
            nraw = old.sub(new, raw)
        if raw == nraw and not missing_ok:
            raise ValueError('Failed (pattern not found) to patch: ' + path)
        f.seek(0), f.truncate()
        f.write(nraw)


@contextmanager
def current_dir(path):
    cwd = os.getcwd()
    os.chdir(path)
    yield path
    os.chdir(cwd)


def windows_cmake_build(
        headers=None, binaries=None, libraries=None, header_dest='include',
        nmake_target='', make='nmake', **kw):
    os.mkdir('build')
    defs = {'CMAKE_BUILD_TYPE': 'Release'}
    cmd = ['cmake', '-G', "NMake Makefiles"]
    for d, val in kw.items():
        if val is None:
            defs.pop(d, None)
        else:
            defs[d] = val
    for k, v in defs.items():
        cmd.append('-D' + k + '=' + v)
    cmd.append('..')
    run(*cmd, cwd='build')
    if nmake_target:
        run(f'{make} {nmake_target}', cwd='build')
    else:
        run(make, cwd='build')
    with current_dir('build'):
        if headers:
            for pat in headers.split():
                copy_headers(pat, header_dest)
        if binaries:
            for pat in binaries.split():
                install_binaries(pat, 'bin')
        if libraries:
            for pat in libraries.split():
                install_binaries(pat)


def cmake_build(
        make_args=(), install_args=(),
        library_path=None, override_prefix=None, no_parallel=False,
        **kw
):
    if isinstance(make_args, str):
        make_args = shlex.split(make_args)
    os.mkdir('build')
    defs = {
        'CMAKE_BUILD_TYPE': 'RELEASE',
        'CMAKE_PREFIX_PATH': PREFIX,
        'CMAKE_INSTALL_PREFIX': override_prefix or build_dir(),
    }
    cmd = ['cmake']
    for d, val in kw.items():
        if val is None:
            defs.pop(d, None)
        else:
            defs[d] = val
    for k, v in defs.items():
        cmd.append('-D' + k + '=' + v)
    cmd.append('..')
    run(*cmd, cwd='build')
    make_opts = [] if no_parallel else split(MAKEOPTS)
    run('make', *(make_opts + list(make_args)), cwd='build')
    mi = ['make'] + list(install_args) + ['install']
    run(*mi, library_path=library_path, cwd='build')


class ModifiedEnv:

    def __init__(self, **kwargs):
        self.mods = kwargs

    def apply(self, mods):
        for k, val in mods.items():
            if val:
                worker_env[k] = val
            else:
                worker_env.pop(k, None)

    def __enter__(self):
        self.orig = {k: worker_env.get(k) for k in self.mods}
        self.apply(self.mods)

    def __exit__(self, *args):
        self.apply(self.orig)


def apply_patch(name, level=0, reverse=False, convert_line_endings=False):
    if not os.path.isabs(name):
        name = os.path.join(PATCHES, name)
    patch = 'C:/cygwin64/bin/patch' if iswindows else 'patch'
    args = [patch, '-p%d' % level, '-i', name]
    if reverse:
        args.insert(1, '-R')
    if iswindows and convert_line_endings:
        run('C:/cygwin64/bin/unix2dos', name)
        args.insert(1, '--binary')
    run(*args)


def install_tree(src, dest_parent='include', ignore=None):
    dest_parent = os.path.join(build_dir(), dest_parent)
    dst = os.path.join(dest_parent, os.path.basename(src))
    if os.path.exists(dst):
        rmtree(dst)
    shutil.copytree(src, dst, symlinks=True, ignore=ignore)
    return dst