#!/usr/bin/env python
# License: GPLv3 Copyright: 2021, Kovid Goyal <kovid at kovidgoyal.net>


from ..constants import PYTHON, iswindows
from ..utils import run, install_binaries


allow_non_universal = True


def main(args):
    run(PYTHON, 'configure.py', '--bootstrap')
    install_binaries('ninja' + ('.exe' if iswindows else ''), destdir='bin')
