#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import build_dir


def main(args):
    os.rename('include', os.path.join(build_dir(), 'include'))
