#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import os
import re
import shutil
import sys

from bypy.constants import CFLAGS, LDFLAGS, LIBDIR, PREFIX, PYTHON, UNIVERSAL_ARCHES, build_dir, is64bit, islinux, ismacos, iswindows
from bypy.utils import ModifiedEnv, copy_headers, get_platform_toolset, get_windows_sdk, install_binaries, replace_in_file, run, simple_build, walk, run_shell
run_shell


def unix_python(args):
    env = {
        'CFLAGS': CFLAGS +
        f' -DHAVE_LOAD_EXTENSION -I{PREFIX}/include/ncursesw'
    }
    if os.path.exists('setup.py'):
        replace_in_file('setup.py', re.compile(b'def detect_tkinter.+:'),
                        lambda m: m.group() + b'\n' + b' ' * 8 + b'return 0')
    conf = (
        '--enable-ipv6 --with-pymalloc --with-system-expat'
        ' --with-lto --enable-optimizations'
        ' --enable-loadable-sqlite-extensions'
        ' --without-ensurepip --with-c-locale-coercion'
    )
    install_args = []
    if islinux:
        conf += f' --enable-shared --prefix={build_dir()}'
        # Needed as the system openssl is too old, causing the _ssl module
        # to fail
        env['LD_LIBRARY_PATH'] = LIBDIR
    elif ismacos:
        # Since python 3.11 python hardcodes the --prefix path for
        # sys.exec_prefix in the Python binary, so we have to use the final
        # installation dir as --prefix. We use symlinks to make it work
        conf += f' --enable-framework={PREFIX}/python'
        conf += f' --with-openssl={PREFIX}'
        # is_pad requires macOS 14.0 (sonoma)
        replace_in_file('configure',
                        'ac_cv_lib_curses_is_pad=yes', 'ac_cv_lib_curses_is_pad=no')
        if len(UNIVERSAL_ARCHES) > 1:
            conf += ' --enable-universalsdk --with-universal-archs=universal2'
            # Without ARCHFLAGS the extensions are built for only one arch
            env['ARCHFLAGS'] = ' '.join(f'-arch {x}' for x in UNIVERSAL_ARCHES)
        # We need rpath for libexpat to load from LIBDIR when loading the
        # _elementtree module which links against it as @rpath/libexpat.1.dylib
        env['LDFLAGS'] = LDFLAGS.replace('-headerpad_max_install_names', '') + f' -rpath {LIBDIR}'
        # dont install IDLE and PythonLauncher
        replace_in_file(
            'Mac/Makefile.in',
            'installapps: install_Python install_PythonLauncher install_IDLE',
            'installapps: install_Python'
        )
        # needed to build universal 3rd party python extensions. See
        # _supports_arm64_builds() in _osx_support.py
        replace_in_file(
            'Lib/_osx_support.py', 'osx_version >= (11, 0)', 'osx_version >= (10, 15)')
        install_args.append(f'PYTHONAPPSDIR={build_dir()}')

        # create the symlink so make install actually installs into build_dir() not --prefix
        if os.path.exists(f'{PREFIX}/python'):
            shutil.rmtree(f'{PREFIX}/python')
        os.mkdir(f'{build_dir()}/python')
        os.symlink(f'{build_dir()}/python', f'{PREFIX}/python')

    try:
        with ModifiedEnv(**env):
            simple_build(conf, relocate_pkgconfig=False, install_args=install_args)
    finally:
        if ismacos:
            os.remove(f'{PREFIX}/python')

    bindir = os.path.join(build_dir(), 'bin')

    def replace_bdir(f, raw=None):
        if raw is None:
            raw = f.read()
        f.seek(0), f.truncate()
        f.write(raw.replace(
            f'{build_dir()}'.encode('utf-8'), PREFIX.encode('utf-8')))

    if not ismacos:
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
    env = {}
    if is64bit:
        env['PROCESSOR_ARCHITECTURE'] = env['PROCESSOR_ARCHITEW6432'] = 'AMD64'

    with open('PCbuild/msbuild.rsp', 'w') as f:
        print(f'/p:PlatformToolset={get_platform_toolset()}', file=f)
        print(f'/p:WindowsTargetPlatformVersion={get_windows_sdk()}', file=f)

    # Inform pythons stupid build scripts where python is located
    pyexe = sys.executable.replace(os.sep, '/')
    replace_in_file('PCbuild\\get_externals.bat', re.compile(br'^call.+find_python.bat.+$', re.MULTILINE),
                    f'set "PYTHON={pyexe}"')
    replace_in_file('PCbuild\\build.bat', re.compile(br'^call.+find_python.bat.+$', re.MULTILINE),
                    f'set "PYTHON={pyexe}"')
    try:
        # Download the prebuilt external binary deps
        run('PCbuild\\get_externals.bat', '--no-tkinter', env=env)
        # use external OpenSSL
        openssl_dir = os.path.abspath(glob.glob('externals/openssl-bin-*/' + ('amd64' if is64bit else 'win32'))[0])
        print(openssl_dir)
        shutil.rmtree(openssl_dir)
        os.makedirs(os.path.join(openssl_dir, 'include'))
        for pat in (
            'bin/libssl*.dll', 'bin/libssl*.pdb', 'bin/libcrypto*.dll', 'bin/libcrypto*.pdb',
            'lib/libssl*.lib', 'lib/libcrypto*.lib'
        ):
            for f in glob.glob(os.path.abspath(os.path.join(PREFIX, pat))):
                shutil.copyfile(f, os.path.join(openssl_dir, os.path.basename(f)))
        shutil.copytree(os.path.join(PREFIX, 'include', 'openssl'), os.path.join(openssl_dir, 'include', 'openssl'))
        shutil.copyfile(os.path.join(PREFIX, 'include', 'openssl', 'applink.c'), os.path.join(openssl_dir, 'include', 'applink.c'))
        libssl = glob.glob(os.path.join(openssl_dir, 'libssl*.dll'))[0]
        suffix = os.path.basename(libssl).split('.')[0][len('libssl'):]
        replace_in_file('PCbuild/openssl.props', re.compile(r'<_DLLSuffix>.+?<OpenSSLDLLSuffix', re.DOTALL),
            f'<_DLLSuffix>{suffix}</_DLLSuffix>\n<OpenSSLDLLSuffix'
        )

        run(
            'PCbuild\\build.bat', '--no-tkinter', '-c',
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
            r'_winreg = _mimetypes_read_windows_registry = None')

        bindir = 'PCbuild\\amd64' if is64bit else 'PCbuild\\win32'
        install_binaries(bindir + os.sep + '*.exe', 'private\\python')
        install_binaries(bindir + os.sep + 'python*.dll', 'private\\python')
        install_binaries(bindir + os.sep + '*.pyd', 'private\\python\\DLLs')
        install_binaries(bindir + os.sep + '*.dll', 'private\\python\\DLLs')
        for pat in ('python*.dll', 'libcrypto*.dll', 'libssl*.dll'):
            for x in glob.glob(os.path.join(build_dir(), r'private\python\DLLs', pat)):
                os.remove(x)
        install_binaries(bindir + os.sep + '*.lib', 'private\\python\\libs')
        copy_headers('PC\\pyconfig.h', 'private\\python\\include')
        copy_headers('Include\\*.h', 'private\\python\\include')
        copy_headers('Include\\cpython', 'private\\python\\include')
        copy_headers('Include\\internal', 'private\\python\\include')
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
    if ismacos:
        # this is a non-universal python launcher
        if parts and parts[-1].endswith('-intel64'):
            return True
    return False


def install_name_change_predicate(p):
    return p.endswith('/Python')


def post_install_check():
    mods = '_ssl _hashlib zlib bz2 ctypes sqlite3 lzma math _elementtree'.split()
    if not iswindows:
        mods.extend('readline _curses'.split())
    run(PYTHON, '-c', 'import sys; print(sys.prefix, sys.exec_prefix); import ' + ','.join(mods), library_path=True)
    run(PYTHON, '-c', 'import sqlite3; c = sqlite3.Connection(":memory:");'
        'c.enable_load_extension(True)', library_path=True)
