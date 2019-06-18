#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import iswindows, PYTHON, build_dir, PREFIX
from bypy.utils import run, python_install

if iswindows:
    def main(args):
        run(PYTHON, 'setup.py', 'fetch', '--all', '--missing-checksum-ok', 'build', 'install', '--root', build_dir())
        python_install()


def install_name_change_predicate(x):
    return x.endswith('apsw.so')


def install_name_change(old_name, is_dep):
    bn = os.path.basename(old_name)
    if bn.startswith('libsqlite'):
        return os.path.join(PREFIX, 'lib', bn)
    return old_name
