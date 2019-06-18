#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re

from bypy.constants import (PERL, PREFIX, PYTHON, RUBY, build_dir, islinux,
                            iswindows)
from bypy.utils import apply_patch, cmake_build, replace_in_file, run, walk

DISABLE_DIRECTIVES = dict(
    ENABLE_TOOLS='OFF', ENABLE_WEBKIT2='OFF',
    # No video
    ENABLE_VIDEO='OFF',
    USE_GSTREAMER='OFF',
    USE_MEDIA_FOUNDATION='OFF',
    # libhyphen is needed for automatic hyphenation on Linux
    USE_LIBHYPHEN='OFF',
    # Dont build tests
    ENABLE_API_TESTS='OFF', ENABLE_TEST_SUPPORT='OFF',
)


def fs(x):
    return x.replace('\\', '/')


def windows_build():
    append_to_path = fr'{PREFIX}\private\gnuwin32\bin'
    append_to_path += fr';{os.path.dirname(RUBY)}'
    append_to_path += fr';{os.path.dirname(PYTHON)}'
    append_to_path += fr';{os.path.dirname(PERL)}'
    env = {
        'WEBKIT_LIBRARIES': f'{PREFIX}',
        'WebKitLibrariesDir': f'{PREFIX}',
    }
    disables = ' '.join(f'-D{k}={v}' for k, v in DISABLE_DIRECTIVES.items())
    script = 'Tools/Scripts/build-webkit'
    icu = ' '.join(f'{fs(PREFIX)}/lib/icu{x}.lib'
                   for x in 'io dt tu uc in'.split())
    for f in 'Qt Win'.split():
        replace_in_file(
            f'Source/cmake/Options{f}.cmake',
            re.compile(r'^\s*set.ICU_LIBRARIES.+', re.M),
            f'set(ICU_LIBRARIES {icu})')
    replace_in_file(
        'Source/CMakeLists.txt',
        'WEBKIT_SET_EXTRA_COMPILER_FLAGS(WebCoreTestSupport ${ADDITIONAL_COMPILER_FLAGS})',  # noqa
        '')
    replace_in_file(
        'Source/CMakeLists.txt',
        'WEBKIT_SET_EXTRA_COMPILER_FLAGS(WebCore ${ADDITIONAL_COMPILER_FLAGS})',  # noqa
        '')
    cmakeargs = (
        f'-Wno-dev -DCMAKE_PREFIX_PATH={fs(PREFIX)};{fs(PREFIX)}/qt'
        f' -DSQLITE3_SOURCE_DIR={fs(PREFIX)}/qt'
        f' {disables}')
    replace_in_file(
        script,
        '(system("perl Tools/Scripts/update-qtwebkit-win-libs") == 0) or die;',
        'print STDERR "Skipping deps download"')
    with open('Source/WebCore/CMakeLists.txt', 'w') as f:
        f.write('\nadd_definitions(-D_DISABLE_EXTENDED_ALIGNED_STORAGE)\n')
    run(
        PERL, script, '--qt', '--release',
        f'--prefix={build_dir()}', '--install',
        f'--cmakeargs', f'{cmakeargs}',
        append_to_path=append_to_path, env=env
    )


def main(args):
    # Control font hinting
    apply_patch('webkit_control_hinting.patch')
    if iswindows:
        return windows_build()

    # fix detection of python2
    if islinux:
        replace_in_file(
            'Source/cmake/WebKitCommon.cmake',
            'find_package(PythonInterp 2.7.0 REQUIRED)',
            'set(PYTHONINTERP_FOUND "ON")\n'
            'set(PYTHON_EXECUTABLE /usr/bin/python2)'
        )

    cmake_build(
        PORT='Qt',
        CMAKE_PREFIX_PATH='{0};{0}/qt'.format(PREFIX),
        override_prefix=os.path.join(build_dir(), 'qt'),
        library_path=True,
        **DISABLE_DIRECTIVES
    )

    for path in walk(build_dir()):
        if path.endswith('.pri'):
            replace_in_file(path, build_dir(), PREFIX)
