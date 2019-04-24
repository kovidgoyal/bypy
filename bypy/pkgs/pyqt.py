#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os

from .constants import PYTHON, MAKEOPTS, build_dir, PREFIX, isosx, iswindows
from .utils import run, replace_in_file


def main(args):
    b = build_dir()
    if isosx:
        b = os.path.join(b, 'python/Python.framework/Versions/2.7')
    elif iswindows:
        b = os.path.join(b, 'private', 'python')
    lp = os.path.join(PREFIX, 'qt', 'lib')
    sip, qmake = 'sip', 'qmake'
    if iswindows:
        sip += '.exe'
        qmake += '.exe'
    sp = 'Lib' if iswindows else 'lib/python2.7'
    cmd = [PYTHON, 'configure.py', '--confirm-license', '--sip=%s/bin/%s' % (PREFIX, sip), '--qmake=%s/qt/bin/%s' % (PREFIX, qmake),
           '--bindir=%s/bin' % b, '--destdir=%s/%s/site-packages' % (b, sp), '--verbose', '--sipdir=%s/share/sip/PyQt5' % b,
           '--no-stubs', '-c', '-j5', '--no-designer-plugin', '--no-qml-plugin', '--no-docstrings']
    if iswindows:
        cmd.append('--spec=win32-msvc2015')
        cmd.append('--sip-incdir=%s/private/python/include' % PREFIX)
    run(*cmd, library_path=lp)
    if iswindows:
        # In VisualStudio 15 Update 3 the compiler crashes on the below
        # statement
        replace_in_file('QtGui/sipQtGuipart2.cpp', 'return new  ::QPicture[sipNrElem]', 'return NULL')
        run('nmake')
        run('nmake install')
    else:
        run('make ' + MAKEOPTS, library_path=lp)
        run('make install')


def post_install_check():
    run(PYTHON, '-c', 'import sip, sipconfig; from PyQt5 import QtCore, QtGui, QtWebKit', library_path=os.path.join(PREFIX, 'qt', 'lib'))
