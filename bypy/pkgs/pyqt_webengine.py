#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import os
import re

from bypy.constants import PREFIX, PYTHON, iswindows
from bypy.pkgs.pyqt import run_build, run_configure
from bypy.utils import replace_in_file, run


def main(args):
    run_configure(for_webengine=True)
    if iswindows:
        libs = 'WebEngine|Quick|WebChannel|Qml|Positioning'
        pat = r'(C:\S+?)bin(.Qt5(?:{})\S*?.lib)'.format(libs)
        for fname in glob.glob('*/Makefile.Release'):
            replace_in_file(fname, re.compile(pat), r'\1lib\2')
    run_build()


def post_install_check():
    run(PYTHON,
        '-c',
        'from PyQt5 import QtWebEngine',
        library_path=os.path.join(PREFIX, 'qt', 'lib'))
