#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


import os

from bypy.constants import islinux
from bypy.utils import qt_build, total_physical_ram


def main(args):
    ram_limit = 24
    if total_physical_ram() < ((ram_limit - 0.5) * 1024**3):
        raise SystemExit(f'Need at least {ram_limit}GB of RAM to build qt-webengine')
    conf = '-feature-qtwebengine-build -feature-qtwebengine-widgets-build'
    conf += ' -no-feature-qtwebengine-quick-build'
    if islinux:
        # use system ICU otherwise there is 10MB duplication and we have to
        # make resources/icudtl.dat available in the application
        conf += ' -webengine-icu'

    qt_build(conf, for_webengine=True)


def is_ok_to_check_universal_arches(x):
    return os.path.basename(x) not in ('gn',)
