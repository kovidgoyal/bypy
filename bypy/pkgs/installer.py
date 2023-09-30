#!/usr/bin/env python
# License: GPLv3 Copyright: 2023, Kovid Goyal <kovid at kovidgoyal.net>


import os
import zipfile

from bypy.constants import build_dir
from bypy.utils import relpath_to_site_packages


def main(args):
    dest = os.path.join(build_dir(), relpath_to_site_packages())
    os.makedirs(dest)
    with zipfile.ZipFile('wheel') as zf:
        zf.extractall(dest)
