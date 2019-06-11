#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import iswindows, NMAKE
from bypy.utils import simple_build, run, install_binaries


def main(args):
    if iswindows:
        run(f'"{NMAKE}" -f build\\visualc.mk')
        install_binaries('src\\optipng\\optipng.exe', 'bin',
                         fname_map=lambda x: 'optipng-calibre.exe')
    else:
        simple_build('-with-system-libs')
