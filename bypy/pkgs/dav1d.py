#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2026, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import meson_build


needs_lipo = True


def main(args):
    meson_build(
        enable_tools="false",
        enable_tests="false",
        enable_examples="false",
        default_library="shared",
        needs_nasm=True,
    )
