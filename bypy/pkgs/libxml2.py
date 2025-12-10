#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>


import re

from bypy.constants import PREFIX, build_dir, ismacos, iswindows, qt_webengine_is_used
from bypy.utils import cmake_build, replace_in_file, simple_build, walk


def main(args):
    needs_icu = qt_webengine_is_used()
    if iswindows or ismacos:
        extra = {}
        cmake_build(
            LIBXML2_WITH_ICU='ON' if needs_icu else 'OFF', LIBXML2_WITH_PYTHON='OFF', LIBXML2_WITH_TESTS='OFF',
            LIBXML2_WITH_LZMA='OFF', relocate_pkgconfig=not iswindows, **extra
        )
    else:
        icu = '--with-icu' if needs_icu else '--without-icu'
        simple_build((
            '--disable-dependency-tracking --disable-static --enable-shared'
            ' --without-python --without-debug --with-iconv={0} --disable-silent-rules'
            ' --with-zlib={0} {1}').format(PREFIX, icu))
        for path in walk(build_dir()):
            if path.endswith('/xml2-config'):
                replace_in_file(
                    path, re.compile(b'(?m)^prefix=.+'),
                    f'prefix={PREFIX}')
