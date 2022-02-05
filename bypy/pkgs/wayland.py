#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

from ..utils import meson_build


def main(args):
    meson_build('--default-library=shared -Dtests=false -Ddocumentation=false -Ddtd_validation=false')
