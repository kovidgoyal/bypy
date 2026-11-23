#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


import os
import re

from bypy.constants import islinux, iswindows
from bypy.utils import qt_build, replace_in_file, require_ram


def main(args):
    require_ram(24 if islinux else 8)
    conf = '-feature-qtwebengine-build -feature-qtwebengine-widgets-build'
    conf += ' -no-feature-qtwebengine-quick-build'
    conf += ' -no-feature-webengine-rust-build'
    # we include ffmpeg for Qt Multimedia anyway we already have the proprietary codecs
    conf += ' -webengine-proprietary-codecs'
    if islinux:
        # use system ICU otherwise there is 10MB duplication
        conf += ' -webengine-icu'

    if iswindows:
        replace_in_file('cmake/QtToolchainHelpers.cmake', 'set(x64List x86_64 AMD64', 'set(x64List x86_64 AMD64 amd64') # ))
        # for some reason the MSVC version checks fail
        replace_in_file(
            'configure.cmake',
            re.compile(r'qt_webengine_configure_check\("(visual-studio|msvc-2019|msvc-2022)".+?\)', re.DOTALL),
            '')


    qt_build(conf, for_webengine=True)


def is_ok_to_check_universal_arches(x):
    return os.path.basename(x) not in ('gn',)
