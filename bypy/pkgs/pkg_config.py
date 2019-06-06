#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import simple_build


def main(args):
    simple_build('--with-internal-glib --disable-host-tool')
