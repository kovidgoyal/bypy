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
        relocate_pkgconfig=False,
    )
