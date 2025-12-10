#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import run, install_binaries, copy_headers


def main(args):
    run('make -f Makefile-libbz2_so')
    install_binaries('libbz2*.so*', do_symlinks=True)
    copy_headers('bzlib.h')
