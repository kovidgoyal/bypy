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
        BUILD_TESTING='OFF',
        JPEGXL_STATIC='OFF',
        JPEGXL_WARNINGS_AS_ERRORS='OFF',
        # Release tarballs do not contain the git submodules in third_party
        # so use our builds of highway, brotli and lcms2 instead of
        # skcms
        JPEGXL_FORCE_SYSTEM_HWY='ON',
        JPEGXL_FORCE_SYSTEM_BROTLI='ON',
        JPEGXL_FORCE_SYSTEM_LCMS2='ON',
        JPEGXL_ENABLE_SKCMS='OFF',
        JPEGXL_BUNDLE_LIBPNG='OFF',
        # Only the library is needed
        JPEGXL_ENABLE_TOOLS='OFF',
        JPEGXL_ENABLE_JPEGLI='OFF',
        JPEGXL_ENABLE_JPEGLI_LIBJPEG='OFF',
        JPEGXL_INSTALL_JPEGLI_LIBJPEG='OFF',
        JPEGXL_ENABLE_DEVTOOLS='OFF',
        JPEGXL_ENABLE_BENCHMARK='OFF',
        JPEGXL_ENABLE_EXAMPLES='OFF',
        JPEGXL_ENABLE_FUZZERS='OFF',
        JPEGXL_ENABLE_VIEWERS='OFF',
        JPEGXL_ENABLE_PLUGINS='OFF',
        JPEGXL_ENABLE_DOXYGEN='OFF',
        JPEGXL_ENABLE_MANPAGES='OFF',
        JPEGXL_ENABLE_JNI='OFF',
        JPEGXL_ENABLE_SJPEG='OFF',
        JPEGXL_ENABLE_OPENEXR='OFF',
    )


def install_name_change(old_name, is_dep):
    bn = os.path.basename(old_name)
    if bn.startswith('libjxl') or bn.startswith('libhwy'):
        return os.path.join(PREFIX, 'lib', bn)
    return old_name
