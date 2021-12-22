#!/usr/bin/env python
# License: GPLv3 Copyright: 2021, Kovid Goyal <kovid at kovidgoyal.net>

from ..constants import iswindows
from ..utils import simple_build, run


allow_non_universal = True


def main(args):
    if not iswindows:
        return simple_build()
    run('.\\vcbuild.bat')
