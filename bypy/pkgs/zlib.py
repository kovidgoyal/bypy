#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

from .constants import iswindows
from .utils import run, install_binaries, copy_headers


if iswindows:
    def main(args):
        run('nmake -f win32/Makefile.msc')
        run('nmake -f win32/Makefile.msc test')
        install_binaries('zlib1.dll*', 'bin')
        install_binaries('zlib.lib'), install_binaries('zdll.*')
        copy_headers('zconf.h'), copy_headers('zlib.h')
