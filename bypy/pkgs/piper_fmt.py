#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>


import os
from bypy.constants import build_dir
from bypy.utils import cmake_build

def main(args):
    cmake_build(
        override_prefix=os.path.join(build_dir(), 'piper-fmt'),
        # See CMakeLists.txt in piper for these settings
        FMT_TEST='OFF',
    )
