#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import build_dir


def main(args):
    os.chdir('..')
    dest = os.path.join(build_dir(), 'private')
    os.makedirs(dest)
    os.rename('gnuwin32', os.path.join(dest, 'gnuwin32'))
