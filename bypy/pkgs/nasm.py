#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re

from bypy.constants import NMAKE, PERL, iswindows
from bypy.utils import install_binaries, replace_in_file, run

allow_non_universal = True

if iswindows:
    def main(args):
        # the Makefile has a circular dependency that breaks building under VS
        # 2019, see
        # https://webcache.googleusercontent.com/search?q=cache:s-p9ts472EoJ:https://forum.nasm.us/index.php%3Ftopic%3D2746.0+&cd=6&hl=en&ct=clnk&gl=in
        replace_in_file(
            'Mkfiles/msvc.mak',
            re.compile(rb'\s+\$\(MAKE\) asm\\warnings.time.+?WARNFILES\)', re.DOTALL), '')
        open('asm/warnings.time', 'w').close()

        run(
                NMAKE, '/f', 'Mkfiles/msvc.mak',
                append_to_path=os.path.dirname(PERL))
        install_binaries('./nasm.exe', 'bin')
