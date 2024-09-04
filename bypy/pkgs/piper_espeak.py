#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>


import os
from bypy.constants import build_dir
from bypy.utils import cmake_build

def main(args):
    cmake_build(
        override_prefix=os.path.join(build_dir(), 'espeak'), relocate_pkgconfig=False,
        # See CMakeLists.txt in piper-phonemize for these settings
        USE_ASYNC='OFF',
        BUILD_SHARED_LIBS='ON',
        USE_MBROLA='OFF',
        USE_LIBSONIC='OFF',
        USE_LIBPCAUDIO='OFF',
        USE_KLATT='OFF',
        USE_SPEECHPLAYER='OFF',
        EXTRA_cmn='ON',
        EXTRA_ru='ON',
        CMAKE_C_FLAGS="-D_FILE_OFFSET_BITS=64",
    )
