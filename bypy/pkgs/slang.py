#!/usr/bin/env python
# License: GPLv3 Copyright: 2025, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys

from bypy.utils import cmake_build


def main(args):
    cmake_build(
        Python3_EXECUTABLE=os.path.abspath(sys.executable),
        SLANG_SLANG_LLVM_FLAVOR='DISABLE',
        SLANG_ENABLE_DXIL='OFF',
        SLANG_ENABLE_OPTIX='OFF',
        SLANG_ENABLE_CUDA='OFF',
        SLANG_ENABLE_SLANGD='OFF',
        SLANG_ENABLE_EXAMPLES='OFF',
        SLANG_ENABLE_GFX='OFF',
        SLANG_ENABLE_TESTS='OFF',
        SLANG_ENABLE_SLANGRT='OFF',
        # SLANG_LIB_TYPE='STATIC',
        SLANG_EMBED_CORE_MODULE='TRUE',
        SLANG_EMBED_CORE_MODULE_SOURCE='TRUE',
        relocate_pkgconfig=False,
    )
