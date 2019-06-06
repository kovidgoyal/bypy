#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import os

from bypy.constants import PREFIX, islinux
from bypy.utils import qt_build


def main(args):
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
    qt_build('-webp -spellchecker -webengine-icu')
