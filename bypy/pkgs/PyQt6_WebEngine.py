#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import PREFIX, PYTHON
from bypy.pkgs.PyQt6 import run_sip_install
from bypy.utils import run


def main(args):
    run_sip_install(for_webengine=True)


def post_install_check():
    run(PYTHON,
        '-c',
        'from PyQt6 import QtWebEngineCore',
        library_path=os.path.join(PREFIX, 'qt', 'lib'))
