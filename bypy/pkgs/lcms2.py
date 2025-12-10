#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import iswindows
from bypy.utils import meson_build

needs_lipo = True

if iswindows:
    def main(args):
        meson_build()
