#!/usr/bin/env python
# License: GPLv3 Copyright: 2025, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import cmake_build

def main(args):
    cmake_build(
        BUILD_SHARED_LIBS='ON', USE_MBROLA='OFF', USE_LIBSONIC='OFF', USE_LIBPCAUDIO='OFF', USE_SPEECHPLAYER='OFF',
    )
