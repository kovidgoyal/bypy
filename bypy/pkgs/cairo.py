#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>



from bypy.utils import meson_build


def main(args):
    meson_build(fontconfig='enabled', freetype='enabled', xcb='disabled', xlib='disabled')
