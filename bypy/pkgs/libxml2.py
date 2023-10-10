#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>


import re

from bypy.constants import PREFIX, build_dir, ismacos, iswindows
from bypy.utils import cmake_build, replace_in_file, simple_build, walk


def main(args):
    if iswindows or ismacos:
        extra = {}
        if iswindows:
            # importing lxml crashes without this. Probably because it is not
            # initializing xml threading and dll import doesnt do it
            # automatically on windows
            extra['LIBXML2_WITH_THREADS'] = 'OFF'
        cmake_build(
            LIBXML2_WITH_ICU='ON', LIBXML2_WITH_PYTHON='OFF', LIBXML2_WITH_TESTS='OFF',
            LIBXML2_WITH_LZMA='OFF', relocate_pkgconfig=not iswindows, **extra
        )
    else:
        # ICU is needed to use libxml2 in qt-webengine
        simple_build(
            '--disable-dependency-tracking --disable-static --enable-shared'
            ' --without-python --without-debug --with-iconv={0} --disable-silent-rules'
            ' --with-zlib={0} --with-icu'.format(PREFIX))
        for path in walk(build_dir()):
            if path.endswith('/xml2-config'):
                replace_in_file(
                    path, re.compile(b'(?m)^prefix=.+'),
                    f'prefix={PREFIX}')
