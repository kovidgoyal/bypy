#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

from ..utils import simple_build


def main(args):
    simple_build('--disable-documentation --disable-static')
