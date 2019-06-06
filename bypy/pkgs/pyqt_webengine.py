#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import PREFIX, PYTHON
from bypy.pkgs.pyqt import run_build, run_configure
from bypy.utils import run


def main(args):
    run_configure(for_webengine=True)
    run_build()


def post_install_check():
    run(PYTHON,
        '-c',
        'from PyQt5 import QtWebEngine',
        library_path=os.path.join(PREFIX, 'qt', 'lib'))
