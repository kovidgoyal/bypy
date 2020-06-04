#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import os

from ..constants import build_dir
from ..utils import simple_build


def main(args):
    simple_build()
    pcdir = os.path.join(build_dir(), 'lib/pkgconfig')
    os.makedirs(pcdir)
    pc = os.path.join(build_dir(), 'share/pkgconfig/wayland-protocols.pc')
    os.rename(pc, pc.replace('/share/', '/lib/'))
