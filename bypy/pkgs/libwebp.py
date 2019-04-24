#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

from .constants import iswindows
from .utils import simple_build, run, install_binaries, copy_headers


def main(args):
    if iswindows:
        run('nmake /f Makefile.vc CFG=release-dynamic RTLIBCFG=dynamic OBJDIR=output')
        install_binaries('output/release-dynamic/*/bin/*.dll', 'bin')
        install_binaries('output/release-dynamic/*/lib/*.lib', 'lib')
        copy_headers('src/webp')
    else:
        simple_build('--disable-dependency-tracking --disable-static')
