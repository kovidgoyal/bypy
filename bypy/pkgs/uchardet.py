#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import PREFIX, iswindows
from bypy.utils import cmake_build, windows_cmake_build


def main(args):
    kw = {
        'BUILD_BINARY': '0',
        'BUILD_STATIC': '0',
        'CMAKE_POLICY_VERSION_MINIMUM': '3.5',  # needed on newer cmake
    }
    if iswindows:
        return windows_cmake_build(
            headers='../src/uchardet.h',
            libraries='src/*.lib src/*.exp',
            binaries='src/*.dll',
            **kw)
    return cmake_build(**kw)


def install_name_change(old_name, is_dep):
    bn = os.path.basename(old_name)
    if bn.startswith('libuchardet'):
        return os.path.join(PREFIX, 'lib', bn)
    return old_name
