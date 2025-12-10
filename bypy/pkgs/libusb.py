#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import simple_build


needs_lipo = True


def main(args):
    simple_build('--disable-udev --disable-dependency-tracking --disable-static', no_parallel=True)
