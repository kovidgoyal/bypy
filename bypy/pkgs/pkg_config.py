#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import UNIVERSAL_ARCHES
from bypy.utils import simple_build


def main(args):
    suffix = ''
    if UNIVERSAL_ARCHES:
        flags = ' '.join(f'-arch {x}' for x in UNIVERSAL_ARCHES)
        suffix = f' CFLAGS="{flags}" LDFLAGS="{flags}"'
    simple_build('--with-internal-glib --disable-silent-rules --disable-host-tool' + suffix)
