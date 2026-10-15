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
        HWY_ENABLE_TESTS='OFF',
        HWY_ENABLE_EXAMPLES='OFF',
        HWY_ENABLE_INSTALL='ON',
        HWY_WARNINGS_ARE_ERRORS='OFF',
    )


def install_name_change(old_name, is_dep):
    bn = os.path.basename(old_name)
    if bn.startswith('libhwy'):
        return os.path.join(PREFIX, 'lib', bn)
    return old_name
