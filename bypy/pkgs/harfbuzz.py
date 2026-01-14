#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

from ..constants import ismacos
from ..utils import meson_build


needs_lipo = True


def main(args):
    meson_build(
        glib='disabled', gobject='disabled',
        chafa='disabled',
        graphite2='disabled',
        icu='disabled',
        freetype='disabled' if ismacos else 'enabled',
        coretext='enabled' if ismacos else 'disabled',
        cairo='disabled',
        default_library='shared',
    )
