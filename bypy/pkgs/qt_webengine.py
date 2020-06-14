#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import os

from bypy.constants import PREFIX, islinux, iswindows
from bypy.utils import qt_build, replace_in_file, apply_patch


def main(args):
    conf = '-spellchecker'
    if islinux:
        # workaround for bug in build system, not adding include path for
        # libjpeg when building iccjpeg, and mjpeg_decoder
        jpeg_files = list(glob.glob(f'{PREFIX}/include/*jpeg*.h'))
        jpeg_files += [
            f'{PREFIX}/include/{x}.h'
            for x in 'jerror jconfig jmorecfg'.split()
        ]
        for header in jpeg_files:
            os.symlink(
                header,
                os.path.join('src/3rdparty/chromium',
                             os.path.basename(header)))
        conf += ' -webp -webengine-icu'
        # https://github.com/harfbuzz/harfbuzz/issues/1990
        replace_in_file(
            'src/3rdparty/chromium/third_party/harfbuzz-ng/src/src/hb-icu.cc',
            '#define HB_ICU_STMT(S) do { S } while (0)',
            '#define HB_ICU_STMT(S) do { S; } while (0)'
        )
        # https://chromium-review.googlesource.com/c/v8/v8/+/2136489
        apply_patch('qt-webengine-icu67.patch')
    if iswindows:
        # broken test for 64-bit ness needs to be disabled
        replace_in_file(
            'configure.pri', 'ProgramW6432', 'PROGRAMFILES')
    qt_build(conf, for_webengine=True)
