#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import NMAKE, PERL, iswindows
from bypy.utils import run, install_binaries

if iswindows:
    def main(args):
        run(
                NMAKE, '/f', 'Mkfiles/msvc.mak',
                append_to_path=os.path.dirname(PERL))
        install_binaries('./nasm.exe', 'bin')
