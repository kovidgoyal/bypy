#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import qt_build


def main(args):
    qt_build('-webp -spellchecker -webengine-icu')
