#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
from .constants import iswindows
from .utils import windows_cmake_build


if iswindows:
    def main(args):
        windows_cmake_build(
            BUILD_tools='OFF', BUILD_examples='OFF', BUILD_tests='OFF', BUILD_doc='OFF',
            binaries='expat.dll', libraries='expat.lib', headers='../lib/expat.h ../lib/expat_external.h'
        )
