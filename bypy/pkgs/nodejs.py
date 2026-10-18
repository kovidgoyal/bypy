#!/usr/bin/env python
# License: GPLv3 Copyright: 2021, Kovid Goyal <kovid at kovidgoyal.net>

from ..constants import iswindows, islinux
from ..utils import simple_build, run, require_ram


allow_non_universal = True


def main(args):
    if not iswindows:
        if islinux:
            require_ram(12)
        # gyp uses its own -O3 and puts CFLAGS after it
        return simple_build(optimize=False)
    run('.\\vcbuild.bat')
