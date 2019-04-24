#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os
import shutil

from .constants import PREFIX, build_dir, islinux, CMAKE, LIBDIR, iswindows
from .utils import walk, run, ModifiedEnv, install_binaries, replace_in_file, install_tree, windows_cmake_build, copy_headers


def main(args):
    if iswindows:
        # cmake cannot find openssl
        replace_in_file('CMakeLists.txt', 'FIND_PACKAGE(LIBCRYPTO)',
                        'SET(LIBCRYPTO_FOUND "1")\nSET(LIBCRYPTO_INCLUDE_DIR "{0}/include")\nSET(LIBCRYPTO_LIBRARIES "{0}/lib/libeay32.lib")'.format(
                            PREFIX.replace(os.sep, '/')))
        windows_cmake_build(
            WANT_LIB64='FALSE', PODOFO_BUILD_SHARED='TRUE', PODOFO_BUILD_STATIC='False', FREETYPE_INCLUDE_DIR="{}/include/freetype2".format(PREFIX),
            nmake_target='podofo_shared'
        )
        copy_headers('build/podofo_config.h', 'include/podofo')
        copy_headers('src/*', 'include/podofo')
        for f in walk():
            if f.endswith('.dll'):
                install_binaries(f, 'bin')
            elif f.endswith('.lib'):
                install_binaries(f, 'lib')
    else:
        # cmake cannot find libpng
        replace_in_file('CMakeLists.txt', 'FIND_PACKAGE(PNG)',
                        'SET(PNG_INCLUDE_DIR "{}/include/libpng16")\nSET(PNG_FOUND "1")\nSET(PNG_LIBRARIES "-lpng16")'.format(PREFIX))
        os.mkdir('podofo-build')
        os.chdir('podofo-build')
        with ModifiedEnv(
                CMAKE_INCLUDE_PATH='{}/include'.format(PREFIX),
                CMAKE_LIBRARY_PATH='{}/lib'.format(PREFIX),
                # These are needed to avoid undefined SIZE_MAX errors on older gcc
                # (SIZE_MAX goes away in podofo 0.9.5)
                CXXFLAGS='-D__STDC_LIMIT_MACROS -D__STDC_CONSTANT_MACROS',
        ):
            cmd = [
                CMAKE, '-G', 'Unix Makefiles', '-Wno-dev',
                '-DFREETYPE_INCLUDE_DIR={}/include/freetype2'.format(PREFIX),
                '-DFREETYPE_LIBRARIES=-lfreetype',
                '-DCMAKE_BUILD_TYPE=RELEASE',
                '-DPODOFO_BUILD_LIB_ONLY:BOOL=TRUE',
                '-DPODOFO_BUILD_SHARED:BOOL=TRUE',
                '-DPODOFO_BUILD_STATIC:BOOL=FALSE',
                '-DCMAKE_INSTALL_PREFIX=' + PREFIX,
                '..'
            ]
            run(*cmd)
            run('make VERBOSE=0 podofo_shared')
            install_binaries('src/libpodofo*')
            inc = os.path.join(build_dir(), 'include', 'podofo')
            os.rename(install_tree('../src', ignore=lambda d, children: [x for x in children if not x.endswith('.h') and '.' in x]), inc)
            shutil.copy2('podofo_config.h', inc)
            ldir = os.path.join(build_dir(), 'lib')
            libs = {os.path.realpath(os.path.join(ldir, x)) for x in os.listdir(ldir)}
            if islinux:
                # libpodofo.so has RPATH set which is just wrong. Remove it.
                run('chrpath', '--delete', *list(libs))


pkg_exclude_names = frozenset()


def install_name_change(old_name, is_dep):
    # since we build podofo in-place the normal install name change logic does
    # not work
    if is_dep:
        return old_name
    return os.path.join(LIBDIR, os.path.basename(old_name))
