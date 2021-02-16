#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import simple_build


def main(args):
    simple_build(configure_args=('--disable-obsolete-api'))
