#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


from bypy.constants import islinux
from bypy.utils import qt_build, apply_patch


def main(args):
    conf = '-feature-qtwebengine-build -feature-qtwebengine-widgets-build'
    conf += ' -no-feature-qtwebengine-quick-build'
    if islinux:
        # see https://bugs.launchpad.net/calibre/+bug/1939958
        apply_patch('crbug1213452.diff', level=1)
        # use system ICU otherwise there is 10MB duplication and we have to
        # make resources/icudtl.dat available in the application
        conf += ' -webengine-icu'

    qt_build(conf, for_webengine=True)
