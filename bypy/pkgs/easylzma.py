#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

from .utils import windows_cmake_build


def main(args):
    windows_cmake_build(binaries='*/lib/*.dll */bin/*.exe', libraries='*/lib/*.lib */lib/*.exp', headers='*/include/easylzma')
