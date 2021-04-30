#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import os
import re
import shutil

from bypy.constants import (CFLAGS, LDFLAGS, LIBDIR, PREFIX, PYTHON,
                            UNIVERSAL_ARCHES, build_dir, is64bit, islinux,
                            ismacos, iswindows)
from bypy.utils import (ModifiedEnv, copy_headers, get_platform_toolset,
                        get_windows_sdk, install_binaries, replace_in_file,
                        run, simple_build, walk)


def unix_python(args):
    env = {
        'CFLAGS': CFLAGS +
        f' -DHAVE_LOAD_EXTENSION -I{PREFIX}/include/ncursesw'
    }
    replace_in_file('setup.py', re.compile(b'def detect_tkinter.+:'),
                    lambda m: m.group() + b'\n' + b' ' * 8 + b'return 0')
    conf = (
        '--enable-ipv6 --with-system-expat --with-pymalloc'
        ' --with-lto --enable-optimizations'
        ' --without-ensurepip --with-c-locale-coercion'
    )
    install_args = ()
    if islinux:
        conf += f' --with-system-ffi --enable-shared --prefix={build_dir()}'
        # Needed as the system openssl is too old, causing the _ssl module
        # to fail
        env['LD_LIBRARY_PATH'] = LIBDIR
    elif ismacos:
        conf += f' --enable-framework={build_dir()}/python'
        conf += f' --with-openssl={PREFIX}'
        if len(UNIVERSAL_ARCHES) > 1:
            conf += ' --enable-universalsdk --with-universal-archs=universal2'
            # Without ARCHFLAGS the extensions are built for only one arch
            env['ARCHFLAGS'] = ' '.join(f'-arch {x}' for x in UNIVERSAL_ARCHES)
        # Needed for readline detection
        env['MACOSX_DEPLOYMENT_TARGET'] = '10.14'
        env['LDFLAGS'] = LDFLAGS.replace('-headerpad_max_install_names', '')
        # dont install IDLE and PythonLauncher
        replace_in_file(
            'Mac/Makefile.in',
            'installapps: install_Python install_PythonLauncher install_IDLE',
            'installapps: install_Python'
        )
        install_args = (f'PYTHONAPPSDIR={build_dir()}',)

    with ModifiedEnv(**env):
        simple_build(conf, relocate_pkgconfig=False, install_args=install_args)

    bindir = os.path.join(build_dir(), 'bin')

    def replace_bdir(f, raw=None):
        if raw is None:
            raw = f.read()
        f.seek(0), f.truncate()
        f.write(raw.replace(
            f'{build_dir()}'.encode('utf-8'), PREFIX.encode('utf-8')))

    if ismacos:
        for f in os.listdir(bindir):
            link = os.path.join(bindir, f)
            with open(link, 'r+b') as f:
                raw = f.read()
                if raw.startswith(b'#!/'):
                    replace_bdir(f, raw)
            if os.path.islink(link):
                fp = os.readlink(link)
                nfp = fp.replace(build_dir(), PREFIX)
                if nfp != fp:
                    os.unlink(link)
                    os.symlink(nfp, link)
        libdir = glob.glob(
            f'{build_dir()}/python/Python.framework/'
            'Versions/Current/lib/python*')[0]
        for x in (
            'config-*-darwin/python-config.py',
            '_sysconfigdata__darwin_darwin.py'
        ):
            with open(glob.glob(f'{libdir}/{x}')[0], 'r+b') as f:
                replace_bdir(f)
    else:
        replace_in_file(os.path.join(bindir, 'python3-config'),
                        re.compile(br'^prefix=".+?"', re.MULTILINE),
                        f'prefix="{PREFIX}"')
        libdir = os.path.join(build_dir(), 'lib')
        for x in (
            'python*/config-*-linux-gnu/python-config.py',
            'python*/_sysconfigdata__linux_*-linux-gnu.py',
        ):
            with open(glob.glob(f'{libdir}/{x}')[0], 'r+b') as f:
                replace_bdir(f)
    os.symlink('python3', os.path.join(bindir, 'python'))


def windows_python(args):
    with open('PCbuild/msbuild.rsp', 'w') as f:
        print(f'/p:PlatformToolset={get_platform_toolset()}', file=f)
        print(f'/p:WindowsTargetPlatformVersion={get_windows_sdk()}', file=f)

    # dont need python 3 to get externals, use git instead
    replace_in_file('PCbuild\\get_externals.bat',
                    re.compile(br'^call.+find_python.bat.+$', re.MULTILINE),
                    '')
    env = {}
    if is64bit:
        env['PROCESSOR_ARCHITECTURE'] = env['PROCESSOR_ARCHITEW6432'] = 'AMD64'
    try:
        run(
            'PCbuild\\build.bat', '-e', '--no-tkinter', '-c',
            'Release', '-m', '-p', ('x64' if is64bit else 'Win32'), '-v',
            '-t', 'Build',
            '--pgo',
            env=env
        )
        # Run the tests
        # run('PCbuild\\amd64\\python.exe', 'Lib/test/regrtest.py', '-u',
        #     'network,cpu,subprocess,urlfetch')

        # Do not read mimetypes from the registry
        replace_in_file(
            'Lib\\mimetypes.py',
            re.compile(br'try:.*?import\s+winreg.*?None', re.DOTALL),
            r'_winreg = None')

        bindir = 'PCbuild\\amd64' if is64bit else 'PCbuild\\win32'
        install_binaries(bindir + os.sep + '*.exe', 'private\\python')
        install_binaries(bindir + os.sep + 'python*.dll', 'private\\python')
        install_binaries(bindir + os.sep + '*.pyd', 'private\\python\\DLLs')
        install_binaries(bindir + os.sep + '*.dll', 'private\\python\\DLLs')
        for x in glob.glob(
                os.path.join(build_dir(),
                             'private\\python\\DLLs\\python*.dll')):
            os.remove(x)
        install_binaries(bindir + os.sep + '*.lib', 'private\\python\\libs')
        copy_headers('PC\\pyconfig.h', 'private\\python\\include')
        copy_headers('Include\\*.h', 'private\\python\\include')
        copy_headers('Include\\cpython', 'private\\python\\include')
        with open('Lib/sitecustomize.py', 'w') as f:
            f.write('''
import os
for path in ('{p}/bin', '{p}/qt/bin'):
    if os.path.exists(path):
        os.add_dll_directory(path)
'''.format(p=PREFIX.replace('\\', '/')))

        shutil.copytree('Lib', os.path.join(build_dir(),
                                            'private\\python\\Lib'))
    finally:
        # bloody git creates files with no write permission
        import stat
        for path in walk('externals'):
            os.chmod(path, stat.S_IWRITE)
            os.remove(path)


def main(args):
    (windows_python if iswindows else unix_python)(args)


def filter_pkg(parts):
    if ('idlelib' in parts or 'lib-tk' in parts
            or 'ensurepip' in parts or 'config' in parts
            or 'pydoc_data' in parts or 'Icons' in parts):
        return True
    if iswindows:
        for p in parts:
            if p.startswith('plat-'):
                return True
    return False


def install_name_change_predicate(p):
    return p.endswith('/Python')


def post_install_check():
    mods = '_ssl zlib bz2 ctypes sqlite3 lzma'.split()
    if not iswindows:
        mods.extend('readline _curses'.split())
    run(PYTHON, '-c', 'import ' + ','.join(mods), library_path=True)
