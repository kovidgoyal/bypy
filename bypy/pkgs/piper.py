#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>


import os
from bypy.constants import build_dir, PREFIX
from bypy.utils import cmake_build

def main(args):
    cmake_build(
        override_prefix=os.path.join(build_dir(), 'piper'), relocate_pkgconfig=False,
        CMAKE_VERBOSE_MAKEFILE='ON',
        FMT_DIR=os.path.join(PREFIX, 'piper-fmt').replace(os.sep, '/'),
        SPDLOG_DIR=os.path.join(PREFIX, 'piper-spdlog').replace(os.sep, '/'),
        PIPER_PHONEMIZE_DIR=os.path.join(PREFIX, 'piper-phonemize').replace(os.sep, '/'),
    )
