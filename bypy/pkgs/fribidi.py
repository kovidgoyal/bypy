#!/usr/bin/env python
# License: GPLv3 Copyright: 2026, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import meson_build

needs_lipo = True


def main(args):
    meson_build(
        docs='false',  # needs c2man
        bin='false',
        tests='false',
        default_library='shared',
    )
