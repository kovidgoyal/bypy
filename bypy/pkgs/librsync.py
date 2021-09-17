#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>


from ..utils import cmake_build


def main(args):
    cmake_build(BUILD_RDIFF='0')
