#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>


from bypy.utils import simple_build


allow_non_universal = True


def main(args):
    simple_build('--no-qt-gui', configure_name='./bootstrap')


def filter_pkg(parts):
    return 'Help' in parts


pkg_exclude_extensions = frozenset()
