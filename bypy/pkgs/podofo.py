#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import PREFIX, iswindows
from bypy.utils import (
    cmake_build, copy_headers, install_binaries, walk, windows_cmake_build, replace_in_file
)


def main(args):
    # Linux distros have libtiff but calibre does not bundle libtiff, we dont
    # want libpodofo to link against the system libtiff
    replace_in_file('CMakeLists.txt', 'if(TIFF_FOUND)', 'if(TIFF_FOUND_DISABLED)')

    if iswindows:
        windows_cmake_build(
            WANT_LIB64='FALSE',
            PODOFO_BUILD_STATIC='False',
            FREETYPE_INCLUDE_DIR=f"{PREFIX}/include/freetype2",
            nmake_target='podofo_shared'
        )
        copy_headers('build/src/podofo/podofo_config.h', 'include/podofo')
        copy_headers('src/podofo/*', 'include/podofo')
        for f in walk():
            if f.endswith('.dll'):
                install_binaries(f, 'bin')
            elif f.endswith('.lib'):
                install_binaries(f, 'lib')
    else:
        cmake_build(
            make_args='podofo_shared',
            PODOFO_BUILD_LIB_ONLY='TRUE',
            PODOFO_BUILD_STATIC='FALSE',
        )


def modify_excludes(excludes):
    excludes.discard('doc')
