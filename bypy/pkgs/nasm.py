#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


from bypy.constants import iswindows
from bypy.utils import install_binaries

allow_non_universal = True

if iswindows:
    def main(args):
        # The makefile nasm provides is full of syntax not supported by nmake,
        # cant be bothered to come up with a patch
        install_binaries('./nasm.exe', 'bin')
