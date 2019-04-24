#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os
import re
import glob
import shutil

from .constants import build_dir, CFLAGS, isosx, iswindows, LIBDIR, PREFIX, islinux, PYTHON, is64bit
from .utils import ModifiedEnv, run, simple_build, replace_in_file, install_binaries, copy_headers, walk

if iswindows:
    def main(args):
        # PlatformToolset below corresponds to the version of Visual Studio, here 2015 (14.0)
        # We create externals/nasm-2.11.06 below so that the python build script does not
        # try to download its own nasm instead using the one we installed above (the python
        # build script fails to mark its nasm as executable, and therefore errors out)
        replace_in_file('PCbuild\\build.bat', '%1', '"/p:PlatformToolset=v140"')

        os.makedirs('externals/nasm-2.11.06')
        # os.makedirs('externals/openssl-1.0.2h')
        # os.makedirs('externals/sqlite-3.8.11.0')
        # os.makedirs('externals/bzip2-1.0.6')

        # dont need python 3 to get externals, use git instead
        replace_in_file('PCbuild\\get_externals.bat', re.compile(r'^call.+find_python.bat.+$', re.MULTILINE), '')

        run('PCbuild\\build.bat', '-e', '--no-tkinter', '--no-bsddb', '-c', 'Release', '-m',
            '-p', ('x64' if is64bit else 'Win32'), '-v', '-t', 'Build')
        # Run the tests
        # run('PCbuild\\amd64\\python.exe', 'Lib/test/regrtest.py', '-u', 'network,cpu,subprocess,urlfetch')

        # Do not read mimetypes from the registry
        replace_in_file('Lib\\mimetypes.py', re.compile(r'try:.*?import\s+_winreg.*?None', re.DOTALL), r'_winreg = None')

        bindir = 'PCbuild\\amd64' if is64bit else 'PCbuild'
        install_binaries(bindir + os.sep + '*.exe', 'private\\python')
        install_binaries(bindir + os.sep + 'python*.dll', 'private\\python')
        install_binaries(bindir + os.sep + '*.pyd', 'private\\python\\DLLs')
        install_binaries(bindir + os.sep + '*.dll', 'private\\python\\DLLs')
        for x in glob.glob(os.path.join(build_dir(), 'private\\python\\DLLs\\python*.dll')):
            os.remove(x)
        install_binaries(bindir + os.sep + '*.lib', 'private\\python\\libs')
        copy_headers('PC\\pyconfig.h', 'private\\python\\include')
        copy_headers('Include\\*.h', 'private\\python\\include')
        shutil.copytree('Lib', os.path.join(build_dir(), 'private\\python\\Lib'))
        # bloody git creates files with no write permission
        import stat
        for path in walk('externals'):
            os.chmod(path, stat.S_IWRITE)
            os.remove(path)

else:
    def main(args):
        env = {'CFLAGS': CFLAGS + ' -DHAVE_LOAD_EXTENSION'}
        replace_in_file('setup.py', re.compile('def detect_tkinter.+:'), lambda m: m.group() + '\n' + ' ' * 8 + 'return 0')
        conf = (
            '--prefix={} --with-threads --enable-ipv6 --enable-unicode={}'
            ' --with-system-expat --with-pymalloc --without-ensurepip').format(
            build_dir(), ('ucs2' if isosx or iswindows else 'ucs4'))
        if islinux:
            conf += ' --with-system-ffi --enable-shared'
            # Needed as the system openssl is too old, causing the _ssl module to fail
            env['LD_LIBRARY_PATH'] = LIBDIR
        elif isosx:
            conf += ' --enable-framework={}/python --with-signal-module'.format(build_dir())
            env['MACOSX_DEPLOYMENT_TARGET'] = '10.9'  # Needed for readline detection

        with ModifiedEnv(**env):
            simple_build(conf)

        bindir = os.path.join(build_dir(), 'bin')
        P = os.path.join(bindir, 'python')
        replace_in_file(P + '-config', re.compile(br'^#!.+/bin/', re.MULTILINE), '#!' + PREFIX + '/bin/')
        if isosx:
            bindir = os.path.join(build_dir(), 'bin')
            for f in os.listdir(bindir):
                link = os.path.join(bindir, f)
                if os.path.islink(link):
                    fp = os.readlink(link)
                    nfp = fp.replace(build_dir(), PREFIX)
                    if nfp != fp:
                        os.unlink(link)
                        os.symlink(nfp, link)


def filter_pkg(parts):
    if (
        'idlelib' in parts or 'lib2to3' in parts or 'lib-tk' in parts or 'ensurepip' in parts or 'config' in parts or 'pydoc_data' in parts or 'Icons' in parts
    ):
        return True
    if iswindows:
        for p in parts:
            if p.startswith('plat-'):
                return True
    return False


def install_name_change_predicate(p):
    return p.endswith('/Python')


def post_install_check():
    if iswindows:
        # Ensure the system python27.dll is not being loaded
        run(PYTHON, '-c', "import sys; 'MSC v.1900' not in sys.version and sys.exit(1)")
    mods = '_ssl zlib bz2 ctypes sqlite3'.split()
    if not iswindows:
        mods.extend('readline _curses'.split())
    run(PYTHON, '-c', 'import ' + ','.join(mods), library_path=True)
