#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re
import shutil

from bypy.constants import (
    MAKEOPTS, NMAKE, PREFIX, PYTHON, build_dir, iswindows
)
from bypy.utils import (
    python_install, relpath_to_site_packages, replace_in_file, run, walk
)


def run_sip_install(for_webengine=False):
    qt_bin = f'{PREFIX}/qt/bin'
    qmake = 'qmake' + ('.exe' if iswindows else '')
    args = (
        '--no-docstrings --no-make'
        f' --qmake={qt_bin}/{qmake} --concatenate=5 --verbose'
    ).split()
    if iswindows:
        args.append('--link-full-dll')
    if for_webengine:
        args.extend('--disable QtWebEngineQuick'.split())
    else:
        args.extend(
            '--qt-shared --confirm-license --no-designer-plugin'
            ' --no-qml-plugin'.split()
        )
    run(f'{PREFIX}/bin/sip-build', *args, library_path=True)
    if iswindows:
        # disable distinfo as installing it fails when using INSTALL_ROOT
        replace_in_file('build/Makefile', 'install_distinfo ', ' ')
        run(NMAKE, cwd='build')
        run(NMAKE, 'install', cwd='build',
            env={'INSTALL_ROOT': build_dir()[2:]})
    else:
        run('make ' + MAKEOPTS, cwd='build')
        run(f'make INSTALL_ROOT="{build_dir()}" install',
            cwd='build', library_path=True)
    rp = os.path.join(build_dir(), relpath_to_site_packages())
    for dirpath, dirnames, filenames in os.walk(build_dir()):
        if 'site-packages' in dirnames:
            sp = os.path.join(dirpath, 'site-packages')
            os.makedirs(rp, exist_ok=True)
            for x in os.listdir(sp):
                os.rename(os.path.join(sp, x), os.path.join(rp, x))
            break
    sp_start = relpath_to_site_packages().replace(os.sep, '/').split('/', 1)[0]
    for x in os.listdir(build_dir()):
        if x != sp_start:
            shutil.rmtree(os.path.join(build_dir(), x))

    python_install()


def main(args):
    run_sip_install()
    if iswindows:
        for x in walk(build_dir()):
            parts = x.replace(os.sep, '/').split('/')
            if parts[-2:] == ['PyQt6', '__init__.py']:
                replace_in_file(x, re.compile(r'^find_qt\(\)', re.M), '')
                break
        else:
            raise ValueError(
                f'Failed to find PyQt6 __init__.py to patch in {build_dir()}')


def post_install_check():
    q = 'from PyQt6 import sip, QtCore, QtGui'
    run(PYTHON, '-c', q, library_path=os.path.join(PREFIX, 'qt', 'lib'))
