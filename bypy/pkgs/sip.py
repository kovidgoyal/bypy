#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>


from bypy.utils import python_build, python_install


def main(args):
    python_build()
    python_install(add_scripts=True)
