#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import (MAKEOPTS, PREFIX, PYTHON, build_dir, ismacos,
                            iswindows)
from bypy.utils import replace_in_file, run


def main(args):
    b = build_dir()
    if ismacos:
        b = os.path.join(b, 'python/Python.framework/Versions/2.7')
    elif iswindows:
        b = os.path.join(b, 'private', 'python')
    lp = os.path.join(PREFIX, 'qt', 'lib')
    sip, qmake = 'sip', 'qmake'
    if iswindows:
        sip += '.exe'
        qmake += '.exe'
    sp = 'Lib' if iswindows else 'lib/python2.7'
    cmd = [
        PYTHON, 'configure.py', '--confirm-license',
        '--assume-shared',
        '--sip=%s/bin/%s' % (PREFIX, sip),
        '--qmake=%s/qt/bin/%s' % (PREFIX, qmake),
        '--bindir=%s/bin' % b,
        '--destdir=%s/%s/site-packages' % (b, sp), '--verbose',
        '--sipdir=%s/share/sip/PyQt5' % b, '--no-stubs', '-c', '-j5',
        '--no-designer-plugin', '--no-qml-plugin', '--no-docstrings'
    ]
    if iswindows:
        cmd.append('--spec=win32-msvc2015')
        cmd.append('--sip-incdir=%s/private/python/include' % PREFIX)
    run(*cmd, library_path=lp)
    if iswindows:
        # In VisualStudio 15 Update 3 the compiler crashes on the below
        # statement
        replace_in_file('QtGui/sipQtGuipart2.cpp',
                        'return new  ::QPicture[sipNrElem]', 'return NULL')
        run('nmake')
        run('nmake install')
    else:
        run('make ' + MAKEOPTS, library_path=lp)
        run('make install', library_path=True)


def post_install_check():
    run(PYTHON,
        '-c',
        'from PyQt5 import sip, QtCore, QtGui, QtWebKit',
        library_path=os.path.join(PREFIX, 'qt', 'lib'))
