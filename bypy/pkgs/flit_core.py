#!/usr/bin/env python
# License: GPLv3 Copyright: 2023, Kovid Goyal <kovid at kovidgoyal.net>


import glob
from bypy.constants import PYTHON
from bypy.utils import run


def main(args):
    run(PYTHON, '-m', 'flit_core.wheel', library_path=True)
    whl = glob.glob('dist/flit_core-*.whl')[0]
    run(PYTHON, 'bootstrap_install.py', whl, library_path=True)
