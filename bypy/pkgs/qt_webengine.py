#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import os

from bypy.constants import PREFIX, islinux, iswindows
from bypy.utils import qt_build, replace_in_file


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
    if iswindows:
        # broken test for 64-bit ness needs to be disabled
        replace_in_file(
            'mkspecs/features/platform.prf', 'ProgramW6432', 'PROGRAMFILES')
    qt_build(conf, for_webengine=True)
