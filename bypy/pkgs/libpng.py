#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os

from .constants import iswindows, PREFIX
from .utils import simple_build, windows_cmake_build


def main(args):
    if iswindows:
        windows_cmake_build(
            PNG_SHARED='1', ZLIB_INCLUDE_DIR=os.path.join(PREFIX, 'include'), ZLIB_LIBRARY=os.path.join(PREFIX, 'lib', 'zdll.lib'),
            binaries='libpng*.dll', libraries='libpng*.lib', headers='pnglibconf.h ../png.h ../pngconf.h'
        )
    else:
        simple_build('--disable-dependency-tracking --disable-static')
