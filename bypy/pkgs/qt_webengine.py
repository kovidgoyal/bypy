#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


import os
from bypy.constants import islinux, iswindows
from bypy.utils import qt_build, total_physical_ram, apply_patch


def main(args):
    if total_physical_ram() < (15.5 * 1024**3):
        raise SystemExit('Need at least 16GB of RAM to build qt-webengine')
    conf = '-feature-qtwebengine-build -feature-qtwebengine-widgets-build'
    conf += ' -no-feature-qtwebengine-quick-build'
    if islinux:
        # use system ICU otherwise there is 10MB duplication and we have to
        # make resources/icudtl.dat available in the application
        conf += ' -webengine-icu'
    elif iswindows:
        # https://code.qt.io/cgit/qt/qtwebengine.git/commit/?id=74163a6511278fa8273ca931ffdf9b9b3a8daae6
        apply_patch('qt6-webengine-windows-n.patch', level=1)

    qt_build(conf, for_webengine=True)


def is_ok_to_check_universal_arches(x):
    return os.path.basename(x) not in ('gn',)
