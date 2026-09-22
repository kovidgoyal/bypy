#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2026, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import PREFIX
from bypy.utils import cmake_build


needs_lipo = True


def main(args):
    cmake_build(
        BUILD_SHARED_LIBS='ON',
        AVIF_CODEC_DAV1D='SYSTEM',
        AVIF_LIBYUV='SYSTEM',
        AVIF_BUILD_APPS='OFF',
        AVIF_BUILD_TESTS='OFF',
        AVIF_BUILD_EXAMPLES='OFF',
    )


def install_name_change(old_name, is_dep):
    bn = os.path.basename(old_name)
    if bn.startswith('libavif'):
        return os.path.join(PREFIX, 'lib', bn)
    return old_name
