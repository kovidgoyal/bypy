#!/usr/bin/env python
# License: GPLv3 Copyright: 2023, Kovid Goyal <kovid at kovidgoyal.net>

import re

from bypy.constants import UNIVERSAL_ARCHES, ismacos, iswindows
from bypy.utils import (
    apply_patch, copy_headers, install_binaries, replace_in_file, run, windows_cmake_build
)


def windows_main(args):
    with open('CMakeLists.txt', 'w') as f:
        f.write('''\
cmake_minimum_required(VERSION 3.6)
project(jbigkit)

set(JBIG_SRC libjbig/jbig.c libjbig/jbig_ar.c)
set(JBIG85_SRC libjbig/jbig85.c libjbig/jbig_ar.c libjbig/jbig_ar.h)

add_library(libjbig STATIC ${JBIG_SRC})
set_target_properties(libjbig PROPERTIES PUBLIC_HEADER "libjbig/jbig_ar.h;libjbig/jbig.h")
add_library(libjbig85 STATIC ${JBIG85_SRC})
set_target_properties(libjbig85 PROPERTIES PUBLIC_HEADER "libjbig/jbig_ar.h;libjbig/jbig85.h")

add_executable(pbmtojbg pbmtools/pbmtojbg.c)
add_executable(pbmtojbg85 pbmtools/pbmtojbg85.c)
add_executable(jbgtopbm pbmtools/pbmtojbg.c)
add_executable(jbgtopbm85 pbmtools/pbmtojbg85.c)

target_include_directories(pbmtojbg PRIVATE libjbig)
target_include_directories(pbmtojbg85 PRIVATE libjbig)
target_include_directories(jbgtopbm PRIVATE libjbig)
target_include_directories(jbgtopbm85 PRIVATE libjbig)

target_link_libraries(pbmtojbg libjbig)
target_link_libraries(pbmtojbg85 libjbig85)
target_link_libraries(jbgtopbm libjbig)
target_link_libraries(jbgtopbm85 libjbig85)

install(TARGETS libjbig libjbig85 pbmtojbg pbmtojbg85 jbgtopbm jbgtopbm85
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
        )
''')
    windows_cmake_build(
        libraries='libjbig.lib',
        headers='../libjbig/jbig.h ../libjbig/jbig85.h ../libjbig/jbig_ar.h',
    )


def unix_main(args):
    apply_patch('jbigkit-2.1-shared_lib.patch', level=1)
    if ismacos:
        replace_in_file('libjbig/Makefile',
            'libjbig.so.$(VERSION)', 'libjbig.$(VERSION).dylib')
        replace_in_file('libjbig/Makefile', '-Wl,-soname,$@', '')
        replace_in_file('libjbig/Makefile',
                        'libjbig85.so.$(VERSION)', 'libjbig85.$(VERSION).dylib')
        replace_in_file('libjbig/Makefile',
                        '%.so: %.so.$(VERSION)', '%.dylib: %.$(VERSION).dylib')
        replace_in_file('libjbig/Makefile',
                        re.compile('all:.+'), 'all: libjbig.dylib libjbig85.dylib')
        arches = ' '.join(f'-arch {x}' for x in UNIVERSAL_ARCHES)
        replace_in_file('libjbig/Makefile', 'CC = gcc', f'CC = gcc {arches}')
    run('make', 'lib')
    copy_headers('libjbig/*.h')
    if ismacos:
        install_binaries('libjbig/*.dylib')
    else:
        install_binaries('libjbig/*.so*')


main = windows_main if iswindows else unix_main
