#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import simple_build


def main(args):
    simple_build('--disable-static --enable-pax_emutramp')
