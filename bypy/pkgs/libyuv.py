#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2026, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import PREFIX, current_build_arch, ismacos
from bypy.utils import cmake_build, replace_in_file


needs_lipo = True


def main(args):
    if ismacos and current_build_arch():
        # libyuv decides whether to compile the NEON/SVE/SME kernels based on
        # CMAKE_SYSTEM_PROCESSOR, but CMake sets that to the host CPU, ignoring
        # CMAKE_OSX_ARCHITECTURES. So when building one slice of the universal
        # binary on a machine with a different CPU the wrong set of kernels is
        # compiled while the common sources (which go by the compiler defined
        # __aarch64__) still reference them, causing link errors. Force the
        # kernel selection to match the arch we are actually compiling for.
        replace_in_file(
            'CMakeLists.txt',
            'string(TOLOWER "${CMAKE_SYSTEM_PROCESSOR}" arch_lowercase)',
            f'set(arch_lowercase "{current_build_arch()}")')
    cmake_build(
        BUILD_SHARED_LIBS='ON',
        UNIT_TEST='OFF',
    )


def install_name_change(old_name, is_dep):
    bn = os.path.basename(old_name)
    if bn.startswith('libyuv'):
        return os.path.join(PREFIX, 'lib', bn)
    return old_name
