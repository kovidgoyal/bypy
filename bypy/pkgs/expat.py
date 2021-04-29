#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import iswindows
from bypy.utils import windows_cmake_build, cmake_build


if iswindows:
    def main(args):
        windows_cmake_build(
            binaries='libexpat.dll', libraries='libexpat.lib',
            headers='../lib/expat.h ../lib/expat_external.h'
        )
else:
    def main(args):
        cmake_build()
