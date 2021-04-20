#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import os

from bypy.constants import PREFIX
from bypy.utils import cmake_build, replace_in_file


def main(args):
    for x in glob.glob('scripts/*.pc.in'):
        replace_in_file(x, '-R${libdir}', '')
    return cmake_build()


def install_name_change(old_name, is_dep):
    bn = os.path.basename(old_name)
    if bn.startswith('libbrotli'):
        return os.path.join(PREFIX, 'lib', bn)
    return old_name
