#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>



from bypy.constants import PREFIX, ismacos, iswindows
from bypy.utils import cmake_build, simple_build


def main(args):
    if ismacos or iswindows:
        cmake_build(
            LIBXSLT_WITH_PYTHON='OFF', LIBXML2_INCLUDE_DIR=f'{PREFIX}/include',
            relocate_pkgconfig=False
        )
    else:
        simple_build(
            '--disable-dependency-tracking --disable-static'
            ' --enable-shared --without-python --without-debug')
