#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re

from bypy.constants import (MAKEOPTS, NMAKE, PREFIX, PYTHON, build_dir,
                            ismacos, iswindows, python_major_minor_version)
from bypy.utils import replace_in_file, run


def run_configure(for_webengine=False):
    pyver = python_major_minor_version()
    b = build_dir()
    if ismacos:
        b = os.path.join(
            b, 'python/Python.framework/Versions/{}.{}'.format(*pyver))
    elif iswindows:
        b = os.path.join(b, 'private', 'python')
    lp = os.path.join(PREFIX, 'qt', 'lib')
    sip, qmake = 'sip', 'qmake'
    if iswindows:
        sip += '.exe'
        qmake += '.exe'
    sp = 'Lib' if iswindows else 'lib/python{}.{}'.format(*pyver)
    sip_dir = f'{b}/share/sip/PyQt5'
    dest_dir = f'{b}/{sp}/site-packages'
    if for_webengine:
        pyqt_options = []
        os.makedirs(sip_dir)
        dest_dir += '/PyQt5'
    else:
        pyqt_options = [
            '--confirm-license',
            '--assume-shared',
            f'--bindir={b}/bin',
            '--no-designer-plugin',
            '--no-qml-plugin',
        ]
    cmd = [PYTHON, 'configure.py'] + pyqt_options + [
        '--sip=%s/bin/%s' % (PREFIX, sip),
        '--qmake=%s/qt/bin/%s' % (PREFIX, qmake),
        f'--destdir={dest_dir}', '--verbose',
        f'--sipdir={sip_dir}', '--no-stubs', '-c', '-j5',
        '--no-docstrings',
    ]
    if iswindows:
        cmd.append('--spec=win32-msvc')
        cmd.append('--sip-incdir=%s/private/python/include' % PREFIX)
        if for_webengine:
            cmd.append(
                f'--pyqt-sipdir={PREFIX}/private/python/share/sip/PyQt5')
    run(*cmd, library_path=lp)
    return dest_dir


def run_build():
    if iswindows:
        run(f'"{NMAKE}"')
        run(f'"{NMAKE}" install')
    else:
        lp = os.path.join(PREFIX, 'qt', 'lib')
        run('make ' + MAKEOPTS, library_path=lp)
        run('make install', library_path=True)


def main(args):
    dest_dir = run_configure()
    run_build()
    if iswindows:
        replace_in_file(
                f'{dest_dir}/PyQt5/__init__.py',
                re.compile(r'^find_qt\(\)', re.M), '')


def post_install_check():
    q = 'from PyQt5 import sip, QtCore, QtGui'
    if iswindows:
        q += ', QtWinExtras'
    run(PYTHON, '-c', q, library_path=os.path.join(PREFIX, 'qt', 'lib'))
