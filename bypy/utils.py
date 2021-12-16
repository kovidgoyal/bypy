#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


import atexit
import ctypes
import errno
import glob
import json
import os
import re
import shlex
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from contextlib import closing, contextmanager, suppress
from functools import partial

from .constants import (
    CMAKE, LIBDIR, MAKEOPTS, NMAKE, PATCHES, PREFIX, PYTHON, UNIVERSAL_ARCHES,
    build_dir, cpu_count, current_build_arch, is64bit,
    is_arm_half_of_lipo_build, islinux, ismacos, iswindows, mkdtemp,
    python_major_minor_version, worker_env
)

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

    def rmtree(x, tries=10):
        shutil.rmtree(x)
    split = shlex.split


hardlink = os.link
ensure_dir = partial(os.makedirs, exist_ok=True)


def print_cmd(cmd):
    end = '\n'
    print('\033[92m', end='')
    end = '\033[m' + end
    print(*cmd, end=end, flush=True)


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


if ismacos:
    def _clean_lock_file(file_obj):
        with suppress(OSError):
            os.remove(file_obj.name)
        with suppress(OSError):
            file_obj.close()

    def single_instance(name):
        import fcntl
        path = os.path.realpath(f'/tmp/si-lock-{name.replace(" ", "_")}')
        f = open(path, 'w')
        try:
            fcntl.lockf(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as err:
            f.close()
            if err.errno not in (errno.EAGAIN, errno.EACCES):
                raise
            return False
        else:
            atexit.register(_clean_lock_file, f)
            return True
elif iswindows:
    import ctypes
    from ctypes import wintypes

    def handlecheck(result, func, args):
        if result == INVALID_HANDLE_VALUE:
            raise ctypes.WinError(ctypes.get_last_error())
        return result

    CreateMutexW = ctypes.windll.kernel32.CreateMutexW
    CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPWSTR]
    CreateMutexW.restype = wintypes.HANDLE
    CreateMutexW.errcheck = handlecheck
    CloseHandle = ctypes.windll.kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL
    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
    ERROR_ALREADY_EXISTS = 0xB7

    def single_instance(name):
        q = f'bypy_si_{name.replace(" ", "_")}'
        try:
            h = CreateMutexW(None, False, q)
        except OSError as err:
            if err.winerror == ERROR_ALREADY_EXISTS:
                return False
            raise
        atexit.register(CloseHandle, h)
        return True
else:
    def single_instance(name):
        import fcntl
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


def atomic_write(path, data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    path = os.path.abspath(path)
    with tempfile.NamedTemporaryFile(dir=os.path.dirname(path), delete=False) as tf:
        tf.write(data)
    os.replace(tf.name, path)


def current_env(library_path=False):
    env = os.environ.copy()
    env.update(worker_env)
    if library_path and islinux:
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
    print('''\033]2;%s\007''' % x)


class RunShell(Exception):

    def __init__(self, library_path, cwd, env):
        Exception.__init__(self, 'Run the shell')
        self.library_path = library_path
        self.cwd = cwd
        self.env = env
        self.serialized = json.dumps({'library_path': library_path, 'cwd': cwd, 'env': env})


def run_shell(library_path=False, cwd=None, env=None):
    if 'BYPY_WORKER' in os.environ:
        raise RunShell(library_path, cwd, env)
    sys.stderr.flush(), sys.stdout.flush()
    if not isatty():
        raise SystemExit('STDOUT is not a tty, aborting...')
    sh = 'C:/cygwin64/bin/zsh' if iswindows else '/bin/zsh'
    env = env or current_env(library_path=library_path)
    if iswindows:
        from .constants import cygwin_paths
        paths = env['PATH'].split(os.pathsep)
        paths = paths + cygwin_paths
        env['PATH'] = os.pathsep.join(paths)
    try:
        if cwd and not os.path.isdir(cwd):
            cwd = None
        try:
            return subprocess.Popen([sh, '-il'], env=env, cwd=cwd).wait()
        except KeyboardInterrupt:
            return 0
    finally:
        # turn off cursor key mode, zsh tends to leave the terminal in that
        # mode when exited with a EOF (ctrl-d)
        sys.stdout.write('\x1b[?1l')
        sys.stdout.flush()


class RunFailure(subprocess.CalledProcessError):

    def __init__(self, rc, cmd, env, cwd):
        subprocess.CalledProcessError.__init__(self, rc, cmd)
        self.env, self.cwd = env, cwd


def run(*args, **kw):
    if len(args) == 1 and isinstance(args[0], str):
        cmd = split(args[0])
    else:
        cmd = list(args)
    print(' '.join(shlex.quote(x) for x in cmd))
    sys.stdout.flush()
    env = current_env(library_path=kw.get('library_path'))
    env.update(kw.get('env', {}))
    append_to_path = kw.get('append_to_path')
    if append_to_path:
        if isinstance(append_to_path, str):
            append_to_path = append_to_path.split(os.pathsep)
        env['PATH'] = os.pathsep.join(
            env['PATH'].split(os.pathsep) + list(append_to_path))
    stdout = subprocess.PIPE if kw.get('get_output') else None
    stdin = subprocess.PIPE if kw.get('stdin') else None
    p = subprocess.Popen(
        cmd, env=env, cwd=kw.get('cwd'), stdout=stdout, stdin=stdin)
    if kw.get('stdin'):
        data = kw['stdin']
        if isinstance(data, str):
            data = data.encode('utf-8')
        stdout = p.communicate(data)[0]
    elif kw.get('get_output'):
        stdout = p.stdout.read()
    rc = p.wait()
    if kw.get('no_check'):
        return rc
    if rc != 0:
        raise RunFailure(rc, str(cmd), env, kw.get('cwd'))
    if kw.get('get_output'):
        return stdout


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


def install_package(pkg_path, dest_dir):
    for dirpath, dirnames, filenames in os.walk(pkg_path):
        for x in tuple(dirnames):
            d = os.path.join(dirpath, x)
            if os.path.islink(d):
                filenames.append(x)
                dirnames.remove(x)
                continue
            name = os.path.relpath(d, pkg_path)
            os.makedirs(os.path.join(dest_dir, name), exist_ok=True)
        for x in filenames:
            f = os.path.join(dirpath, x)
            name = os.path.relpath(f, pkg_path)
            lcopy(f, os.path.join(dest_dir, name))


def extract(source, path='.'):
    if source.lower().endswith('.zip'):
        with zipfile.ZipFile(source) as zf:
            zf.extractall(path)
    else:
        with tarfile.open(source, encoding='utf-8') as tf:
            tf.extractall(path)


def chdir_for_extract(name):
    tdir = mkdtemp(prefix=os.path.basename(name).split('-')[0] + '-')
    os.chdir(tdir)
    return tdir


def extract_source_and_chdir(source):
    tdir = chdir_for_extract(source)
    st = time.monotonic()
    print('Extracting source:', source)
    sys.stdout.flush()
    extract(source)
    x = os.listdir('.')
    if len(x) == 1:
        for y in os.listdir(x[0]):
            os.rename(os.path.join(x[0], y), y)
        os.rmdir(x[0])
    print('Extracted in', int(time.monotonic() - st), 'seconds')
    return tdir


def relocate_pkgconfig_files():
    for path in walk(build_dir()):
        if path.endswith('.pc'):
            if re.search(
                    f'^prefix={PREFIX}$', open(path).read(),
                    flags=re.M) is None:
                replace_in_file(path, build_dir(), PREFIX)
        if path.endswith('.cmake'):
            if build_dir() in open(path).read():
                replace_in_file(path, build_dir(), PREFIX)


def simple_build(
        configure_args=(), make_args=(), install_args=(),
        library_path=None, override_prefix=None, no_parallel=False,
        configure_name='./configure', relocate_pkgconfig=True,
        autogen_name='./autogen.sh', do_install=True,
        use_envvars_for_lipo=False
):
    if isinstance(configure_args, str):
        configure_args = split(configure_args)
    else:
        configure_args = list(configure_args)
    if isinstance(make_args, str):
        make_args = split(make_args)
    if isinstance(install_args, str):
        install_args = split(install_args)
    if not os.path.exists(configure_name) and os.path.exists(autogen_name):
        run(autogen_name)
    env = {}
    if is_arm_half_of_lipo_build():
        flags = f'{worker_env["CFLAGS"]} -arch {current_build_arch()}'
        if use_envvars_for_lipo:
            env.update({'CFLAGS': flags, 'CXXFLAGS': flags, 'LDFLAGS': f'{worker_env["LDFLAGS"]} -arch {current_build_arch()}'})
        else:
            configure_args += [
                '--build=x86_64-apple-darwin', '--host=aarch64-apple-darwin',
                f'CXXFLAGS={flags}', f'CFLAGS={flags}',
            ]
    run(configure_name, '--prefix=' + (
        override_prefix or build_dir()), *configure_args, env=env)
    make_opts = [] if no_parallel else split(MAKEOPTS)
    run('make', *(make_opts + list(make_args)))
    if do_install:
        mi = ['make'] + list(install_args) + ['install']
        run(*mi, library_path=library_path)
        if relocate_pkgconfig:
            relocate_pkgconfig_files()


def qt_build(configure_args='', for_webengine=False, num_jobs=None, **env):
    # To get configure args run qt-configure-module . -help in the module
    # source dir
    os.mkdir('build')
    os.chdir('build')
    append_to_path = [os.path.join(PREFIX, 'qt', 'bin')]
    run('qt-configure-module', '..', '-help',
        append_to_path=append_to_path, library_path=True)
    run('qt-configure-module', '..', '-list-features',
        append_to_path=append_to_path, library_path=True)
    if iswindows:
        append_to_path.append(os.path.dirname(os.environ['PYTHON_TWO']))
        if for_webengine:
            append_to_path.insert(0, f'{PREFIX}/private/gnuwin32/bin')
    if for_webengine:
        pass  # configure_args += ' -no-feature-webengine-jumbo-build'
    run(
        'qt-configure-module', '..', *shlex.split(configure_args.strip()),
        library_path=True, append_to_path=append_to_path or None,
        env=env
    )
    if for_webengine:
        # configure_args += ' -no-feature-webengine-jumbo-build'
        # ninja by default creates cpu_count + 2 jobs, max RAM per job is thus
        # RAM/num_jobs. Linking webengine requires several GB of RAM -- ka blammo
        num = 4 if islinux else 2
        for f in walk('.'):
            if f.endswith('.ninja'):
                replace_in_file(
                    f, 'ninja -C', f'ninja -j {num} -C', missing_ok=True)
    run('cmake --build . --parallel',
        library_path=True, append_to_path=append_to_path, env=env)
    run(f'cmake --install . --prefix {build_dir()}/qt', env=env)
    relocate_pkgconfig_files()
    # if iswindows:
    #     if for_webengine:
    #         os.mkdir('process')
    #     run(f'"{NMAKE}"', append_to_path=append_to_path, **env)
    #     iroot = build_dir()[2:]
    #     run(f'"{NMAKE}" INSTALL_ROOT={iroot} install')
    # else:
    #     run('make ' + MAKEOPTS, library_path=True, **env)
    #     run(f'make INSTALL_ROOT={build_dir()} install')
    # base = os.path.relpath(PREFIX, '/')
    # os.rename(
    #     os.path.join(build_dir(), base, 'qt'), os.path.join(build_dir(), 'qt'))


FAT_MAGIC_BE = struct.pack('>I',    0xcafe_babe)
FAT_MAGIC_LE = struct.pack('<I',    0xcafe_babe)
FAT_MAGIC_64_BE = struct.pack('>I', 0xcafe_babf)
FAT_MAGIC_64_LE = struct.pack('<I', 0xcafe_babf)
MH_MAGIC_BE = struct.pack('>I',     0xfeed_face)
MH_MAGIC_LE = struct.pack('<I',     0xfeed_face)
MH_MAGIC_64_BE = struct.pack('>I',  0xfeed_facf)
MH_MAGIC_64_LE = struct.pack('<I',  0xfeed_facf)
MACH_MAGICS = (
    FAT_MAGIC_BE, FAT_MAGIC_LE, FAT_MAGIC_64_BE, FAT_MAGIC_64_LE,
    MH_MAGIC_BE, MH_MAGIC_LE, MH_MAGIC_64_BE, MH_MAGIC_64_LE
)


def is_macho_binary(p):
    try:
        with open(p, 'rb') as f:
            return f.read(4) in MACH_MAGICS
    except (FileNotFoundError, IsADirectoryError):
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


def python_prefix():
    current_output_dir = build_dir()
    relpath = os.path.relpath(PREFIX, '/')
    return os.path.join(current_output_dir, relpath)


def python_install(add_scripts=False):
    ddir = 'python' if ismacos else 'private' if iswindows else 'lib'
    to_remove = os.listdir(build_dir())[0]
    if ismacos and to_remove == 'Library':
        # python 3.9 changes how it builds things, yet again
        os.rename(
            os.path.join(build_dir(), 'Library', 'Frameworks'),
            os.path.join(build_dir(), ddir))
    else:
        pp = python_prefix()
        os.rename(os.path.join(pp, ddir), os.path.join(build_dir(), ddir))
    if add_scripts:
        if ismacos:
            major, minor = python_major_minor_version()
            os.rename(
                os.path.join(
                    build_dir(), ddir,
                    f'Python.framework/Versions/{major}.{minor}/bin'),
                os.path.join(build_dir(), 'bin'))
        elif iswindows:
            os.rename(os.path.join(build_dir(), ddir, 'python', 'Scripts'),
                      os.path.join(build_dir(), 'bin'))
        else:
            ddir = 'bin'
            os.rename(os.path.join(pp, ddir), os.path.join(build_dir(), ddir))
    rmtree(os.path.join(build_dir(), to_remove))


def get_arches_in_binary(path):
    x = subprocess.check_output([
        'lipo', '-archs', path]).decode('utf-8').strip()
    return {y for y in x.split()}


def create_package(module, outpath):

    exclude = getattr(module, 'pkg_exclude_names', set(
        'doc man info test tests gtk-doc README'.split()))
    if hasattr(module, 'modify_excludes'):
        module.modify_excludes(exclude)
    exclude_extensions = getattr(module, 'pkg_exclude_extensions', set((
        'pyc', 'pyo', 'la', 'chm', 'cpp', 'rst', 'md')))
    if hasattr(module, 'modify_exclude_extensions'):
        module.modify_exclude_extensions(exclude_extensions)

    with suppress(FileNotFoundError):
        shutil.rmtree(outpath)

    os.makedirs(outpath)
    check_universal_binaries = ismacos and len(
        UNIVERSAL_ARCHES) > 1 and not getattr(
            module, 'allow_non_universal', False)
    dylibs = set()
    src_dir = build_dir()

    for dirpath, dirnames, filenames in os.walk(src_dir):

        def get_name(x):
            return os.path.relpath(os.path.join(dirpath, x),
                                   src_dir).replace(os.sep, '/')

        def is_ok(name):
            parts = name.split('/')
            for p in parts:
                if p in exclude or (
                    '.' in p and p.rpartition('.')[-1] in exclude_extensions
                ):
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
                full_path = os.path.realpath(os.path.join(outpath, name))
                if check_universal_binaries and full_path not in dylibs and (
                        name.endswith('.dylib') or is_macho_binary(full_path)):
                    dylibs.add(full_path)
    expected = set(UNIVERSAL_ARCHES)
    for x in dylibs:
        arches = get_arches_in_binary(x)
        if arches != expected:
            print(
                f'The file {x} is not a universal binary.'
                f' Copied from {src_dir}.'
                f' It only has arches: {arches}', file=sys.stderr)
            shutil.rmtree(outpath)
            raise SystemExit('Failed to build universal binary')


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
    return files


def replace_in_file(path, old, new, missing_ok=False):
    if isinstance(old, str):
        old = old.encode('utf-8')
    if isinstance(new, str):
        new = new.encode('utf-8')
    with open(path, 'r+b') as f:
        raw = f.read()
        if isinstance(old, bytes):
            nraw = raw.replace(old, new)
            pat_repr = old.decode('utf-8')
        else:
            if isinstance(old.pattern, str):
                old = re.compile(
                    old.pattern.encode('utf-8'), old.flags & ~re.UNICODE)
            nraw = old.sub(new, raw)
            pat_repr = old.pattern.decode('utf-8')
        replaced = raw != nraw
        if not replaced and not missing_ok:
            raise ValueError(
                f'Failed (pattern "{pat_repr}" not found) to patch: {path}')
        f.seek(0), f.truncate()
        f.write(nraw)
        return replaced


@contextmanager
def current_dir(path):
    cwd = os.getcwd()
    os.chdir(path)
    yield path
    os.chdir(cwd)


@contextmanager
def timeit():
    ' Usage: `with timeit() as times: whatever()` minutes, seconds = times '
    times = [0, 0]
    st = time.monotonic()
    yield times
    dt = int(time.monotonic() - st)
    times[0], times[1] = dt // 60, dt % 60


def windows_cmake_build(
        headers=None, binaries=None, libraries=None, header_dest='include',
        nmake_target='', make=NMAKE, **kw):
    os.mkdir('build')
    defs = {'CMAKE_BUILD_TYPE': 'Release'}
    cmd = [CMAKE, '-G', "NMake Makefiles"]
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


def get_platform_toolset():
    from bypy.constants import vcvars_env
    return 'v' + vcvars_env['VCTOOLSVERSION'].replace('.', '')[:3]


def get_windows_sdk():
    from bypy.constants import vcvars_env
    return vcvars_env['WINDOWSSDKVERSION'].strip('\\')


def windows_sdk_paths():
    sd = worker_env['WINDOWSSDKDIR']
    sdv = worker_env['WINDOWSSDKVERSION']
    return {
        'include': os.path.join(sd, 'Include', sdv).rstrip(os.sep),
        'lib': os.path.join(sd, 'Lib', sdv, 'um'),
    }


def msbuild(proj, *args, configuration='Release', **env):
    global worker_env
    from bypy.constants import vcvars_env
    from bypy.vcvars import find_msbuild
    PL = 'x64' if is64bit else 'Win32'
    sdk = get_windows_sdk()
    orig_worker_env = worker_env.copy()
    # MSBuild should not run in the vcvars environment as it
    # sets up its own tools and paths
    for k in vcvars_env:
        worker_env.pop(k, None)
    try:
        run(
            find_msbuild(), proj, '/t:Build', f'/p:Platform={PL}',
            f'/p:Configuration={configuration}',
            f'/p:PlatformToolset={get_platform_toolset()}',
            f'/p:WindowsTargetPlatformVersion={sdk}', *args, **env
        )
    finally:
        worker_env = orig_worker_env


def cmake_build(
        make_args=(), install_args=(),
        library_path=None, override_prefix=None, no_parallel=False,
        relocate_pkgconfig=True, append_to_path=None, env=None,
        **kw
):
    make = NMAKE if iswindows else 'make'
    if isinstance(make_args, str):
        make_args = shlex.split(make_args)
    os.mkdir('build')
    defs = {
        'CMAKE_BUILD_TYPE': 'RELEASE',
        'CMAKE_SYSTEM_PREFIX_PATH': PREFIX,
        'CMAKE_INSTALL_PREFIX': override_prefix or build_dir(),
    }
    if ismacos:
        defs.update({
            # tell cmake to use our zlib
            'CMAKE_POLICY_DEFAULT_CMP0074': 'NEW',
            'ZLIB_ROOT': f'{PREFIX}',
        })
    if len(UNIVERSAL_ARCHES) > 1 and ismacos:
        if current_build_arch():
            defs['CMAKE_OSX_ARCHITECTURES'] = current_build_arch()
        else:
            defs['CMAKE_OSX_ARCHITECTURES'] = ';'.join(UNIVERSAL_ARCHES)
    if iswindows:
        cmd = [CMAKE, '-G', "NMake Makefiles"]
    else:
        cmd = [CMAKE]
    for d, val in kw.items():
        if val is None:
            defs.pop(d, None)
        else:
            defs[d] = val
    for k, v in defs.items():
        cmd.append('-D' + k + '=' + v)
    cmd.append('..')
    env = env or {}
    run(*cmd, cwd='build', append_to_path=append_to_path, env=env)
    make_opts = []
    if not iswindows:
        make_opts = [] if no_parallel else split(MAKEOPTS)
    run(make, *(make_opts + list(make_args)),
        cwd='build', env=env, append_to_path=append_to_path)
    mi = [make] + list(install_args) + ['install']
    run(*mi, library_path=library_path, cwd='build')
    if relocate_pkgconfig:
        relocate_pkgconfig_files()


def meson_build(extra_cmdline='', library_path=None, **options):
    cmd = [
        'meson', '--buildtype=release', f'--prefix={build_dir()}',
        f'--libdir={build_dir()}/lib'
    ]
    if extra_cmdline:
        cmd += shlex.split(extra_cmdline)
    cmd += [f'-D{k}={v}' for k, v in options.items()]
    cmd.append('build')
    run(*cmd)
    run('ninja -C build', library_path=library_path)
    run('ninja -C build install', library_path=library_path)
    relocate_pkgconfig_files()


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


def run_worker(job, decorate=True):
    cmd, human_text = job
    human_text = human_text or ' '.join(cmd)
    env = os.environ.copy()
    env.update(worker_env)
    if islinux:
        env['LD_LIBRARY_PATH'] = LIBDIR
    try:
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    except Exception as err:
        return False, human_text, str(err)
    stdout, stderr = p.communicate()
    stdout = (stdout or b'').decode('utf-8', 'replace')
    stderr = (stderr or b'').decode('utf-8', 'replace')
    if decorate:
        stdout = human_text + '\n' + stdout
    ok = p.returncode == 0
    return ok, stdout, stderr


def create_job(cmd, human_text=None):
    return (cmd, human_text)


def parallel_build(jobs, log=print, verbose=True):
    from multiprocessing.dummy import Pool
    p = Pool(cpu_count())
    with closing(p):
        for ok, stdout, stderr in p.imap(run_worker, jobs):
            if verbose or not ok:
                log(stdout)
                if stderr:
                    log(stderr)
            if not ok:
                return False
        return True


def py_compile(basedir, optimization_level='-OO'):
    version = python_major_minor_version()[0]
    if version < 3:
        run(
            PYTHON, optimization_level, '-m', 'compileall', '-d', '', '-f',
            '-q', basedir, library_path=True)
        clean_exts = ('py', 'pyc')
    else:
        run(
            PYTHON, optimization_level, '-m', 'compileall', '-d', '', '-f',
            '-q', '-b', '-j', '0', '--invalidation-mode=unchecked-hash',
            basedir, library_path=True)
        clean_exts = ('py',)

    for f in walk(basedir):
        ext = f.rpartition('.')[-1].lower()
        if ext in clean_exts:
            os.remove(f)


def get_dll_path(base, levels=1, loc=LIBDIR):
    pat = f'lib{base}.so.*'
    candidates = tuple(glob.glob(os.path.join(loc, pat)))
    if not candidates:
        candidates = sorted(
            glob.glob(os.path.join(loc, '*', pat)), reverse=True)

    for x in candidates:
        q = os.path.basename(x)
        q = q[q.rfind('.so.'):][4:].split('.')
        if len(q) == levels:
            return x
    raise ValueError(f'Could not find library for base name: {base}')


def dos2unix(path):
    with open(path, 'rb') as f:
        raw = f.read().replace(b'\r\n', b'\n')
    with open(path, 'wb') as f:
        f.write(raw)


def binaries_in(base):
    base = os.path.abspath(os.path.realpath(base))
    for x in walk(base):
        x = os.path.realpath(x)
        if x.endswith('.dylib') or is_macho_binary(x):
            yield os.path.relpath(os.path.abspath(x), base)


def lipo(output_dirs):
    output_dir = build_dir()
    binary_collections = set()
    for xa, x in output_dirs:
        binary_collections.add(frozenset(binaries_in(x)))
    if len(binary_collections) > 1:
        raise SystemExit(
            'The set of binaries is different across different'
            ' target architectures, cannot lipo them')
    binaries = tuple(binary_collections)[0]
    install_package(output_dirs[0][1], output_dir)

    for binary in binaries:
        dst = os.path.join(output_dir, binary)
        if os.path.exists(dst):
            os.remove(dst)
        cmd = ['lipo']
        all_arches = []
        for arch, x in output_dirs:
            all_arches.append(arch)
            cmd.extend(('-arch', arch, os.path.join(x, binary)))
        cmd += ['-create', '-output', dst]
        run(*cmd)
        cmd = ['lipo', dst, '-verify_arch'] + all_arches
        run(*cmd)


def setup_program_parser(pa):
    a = pa.add_argument
    a('--dont-strip',
      default=False,
      action='store_true',
      help='Dont strip the binaries when building')
    a('--compression-level',
      default='9',
      choices=list('123456789'),
      help='Level of compression for the Linux tarball')
    a('--skip-tests',
      default=False,
      action='store_true',
      help='Skip the tests when building')
    a('--sign-installers',
      default=False,
      action='store_true',
      help='Sign the binary installer, needs signing keys in the VMs')
    a('--notarize',
      default=False,
      action='store_true',
      help='Send the app for notarization to the platform vendor')
    a('--build-only',
      help='Build only a single extension module when building'
      ' program, useful for development')


def cmdline_for_program(args):
    ans = ['program', '--compression-level', args.compression_level]
    for x in ('dont_strip', 'skip_tests', 'sign_installers', 'notarize'):
        if getattr(args, x):
            ans.append('--' + x.replace('_', '-'))
    if args.build_only:
        ans.extend(('--build-only', args.build_only))
    return ans


def setup_dependencies_parser(p):
    from .download_sources import read_deps
    try:
        deps = read_deps()
    except FileNotFoundError:
        deps = ()
    choices = (x['name'] for x in deps)
    p.add_argument(
        'dependencies', nargs='*',
        help='The dependencies to build. If none are specified missing dependencies only are built. Available deps:' +
        ' '.join(choices)
    )


def cmdline_for_dependencies(args):
    return ['dependencies'] + args.dependencies


def setup_build_parser(p):
    s = p.add_subparsers(dest='action', required=True)
    sp = s.add_parser('shell', help='Open a shell in the build VM')
    sp.add_argument('--send-to-vm', action='store_true', help='Sync data from here to the VM')

    pa = s.add_parser('program', help='Build the actual program')
    setup_program_parser(pa)
    s.add_parser('shutdown', help='Shutdown the VM', aliases=['halt', 'poweroff'])

    setup_dependencies_parser(s.add_parser('dependencies', aliases=['deps']))
    return s
