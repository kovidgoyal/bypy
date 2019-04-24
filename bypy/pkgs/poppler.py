#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os
import re

from .constants import CFLAGS, PREFIX, isosx, MAKEOPTS, iswindows
from .utils import run, ModifiedEnv, install_binaries, simple_build, windows_cmake_build, replace_in_file


def main(args):
    if iswindows:
        # poppler unconditionally searches for Qt5, which we dont want
        replace_in_file('CMakeLists.txt', re.compile(r'^if\([^)]+2.8.7\)$.+?^endif.+?$', re.MULTILINE | re.DOTALL), 'set(QT5_FOUND false)')
        # Remove macros re-definitions of fmax/fmin as they cause errors
        replace_in_file('poppler/poppler-config.h.cmake', re.compile(r'^#define (fmax|fmin).+$', re.MULTILINE), '')
        # Missing include
        replace_in_file('poppler/PSOutputDev.cc', '#include <config.h>', '#include <config.h>\n#include <algorithm>')

        windows_cmake_build(
            ENABLE_CPP='0', ENABLE_LIBOPENJPEG='OFF', ENABLE_CMS='OFF',
            BUILD_GTK_TESTS='OFF', BUILD_QT4_TESTS='OFF', BUILD_QT5_TESTS='OFF', BUILD_CPP_TESTS='OFF')
        install_binaries('build/utils/*.exe', 'bin')
    else:
        with ModifiedEnv(
            CXXFLAGS=CFLAGS,
            FONTCONFIG_CFLAGS="-I{0}/include/fontconfig -I{0}/include".format(PREFIX),
            FONTCONFIG_LIBS="-L{0}/lib -lfontconfig".format(PREFIX),
            FREETYPE_CFLAGS="-I{0}/include/freetype2 -I{0}/include".format(PREFIX),
            FREETYPE_LIBS="-L{0}/lib -lfreetype -lz -lbz2".format(PREFIX),
            FREETYPE_CONFIG="{0}/bin/freetype-config".format(PREFIX),
            LIBJPEG_LIBS="-L{0}/lib -ljpeg".format(PREFIX),
            LIBPNG_LIBS="-L{0}/lib -lpng".format(PREFIX),
            LIBPNG_CFLAGS="-I{0}/include/libpng16".format(PREFIX),
            UTILS_LIBS="-lfreetype -lfontconfig -ljpeg -lpng"
        ):
            conf = ('--without-x --enable-shared --disable-dependency-tracking  --disable-silent-rules '
                    '--enable-zlib --enable-splash-output --disable-cairo-output --disable-poppler-glib '
                    '--disable-poppler-qt4 --disable-poppler-qt5 --disable-poppler-cpp --disable-gtk-test '
                    '--enable-libjpeg --enable-compile-warnings=no')
            if isosx:
                simple_build(conf)
            else:
                run(('./configure --prefix={} ' + conf).format(PREFIX))
                for x in 'goo fofi splash poppler utils'.split():
                    os.chdir(x)
                    run('make ' + MAKEOPTS)
                    os.chdir('..')
                install_binaries('poppler/.libs/lib*.so*')
                install_binaries('utils/.libs/pdf*', 'bin')
