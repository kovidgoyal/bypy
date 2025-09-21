#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import cmake_build, replace_in_file


def main(args):
    # Linux distros have libtiff but calibre does not bundle libtiff, we dont
    # want libpodofo to link against the system libtiff
    replace_in_file('CMakeLists.txt', 'if(TIFF_FOUND)', 'if(TIFF_FOUND_DISABLED)')

    cmake_build(
        make_args='podofo_shared',
        PODOFO_BUILD_LIB_ONLY='TRUE',
        PODOFO_BUILD_STATIC='FALSE',
    )


def modify_excludes(excludes):
    excludes.discard('doc')
