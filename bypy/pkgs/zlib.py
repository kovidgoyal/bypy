#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import iswindows, NMAKE
from bypy.utils import run, install_binaries, copy_headers


if iswindows:
    def main(args):
        run(f'"{NMAKE}" -f win32/Makefile.msc')
        run(f'"{NMAKE}" -f win32/Makefile.msc test')
        install_binaries('zlib1.dll*', 'bin')
        install_binaries('zlib.lib'), install_binaries('zdll.*')
        copy_headers('zconf.h'), copy_headers('zlib.h')
