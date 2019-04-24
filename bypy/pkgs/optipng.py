#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

from .constants import iswindows
from .utils import simple_build, run, install_binaries


def main(args):
    if iswindows:
        run('nmake -f build\\visualc.mk')
        install_binaries('src\\optipng\optipng.exe', 'bin', fname_map=lambda x: 'optipng-calibre.exe')
    else:
        simple_build('-with-system-libs')
