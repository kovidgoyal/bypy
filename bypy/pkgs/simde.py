#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import shutil

from bypy.constants import build_dir


def main(args):
    dest = os.path.join(build_dir(), 'include/simde')
    shutil.copytree(os.getcwd(), dest)
