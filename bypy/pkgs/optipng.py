#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import iswindows
from bypy.utils import simple_build, windows_cmake_build, install_binaries


needs_lipo = True


def main(args):
    if iswindows:
        windows_cmake_build()
        install_binaries('build\\optipng.exe', 'bin',
                         fname_map=lambda x: 'optipng-calibre.exe')
    else:
        simple_build('-with-system-libs', use_envvars_for_lipo=True)
