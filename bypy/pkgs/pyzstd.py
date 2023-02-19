#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


import os

from bypy.utils import python_build, python_install, walk, build_dir


def main(args):
    python_build("--dynamic-link-zstd")
    for f in walk(build_dir()):
        if os.path.basename(f) == 'c_pyzstd.py':
            q = os.path.join(os.path.dirname(f), '__init__.py')
            if not os.path.exists(q):
                open(q, 'w').close()
            break
    python_install()
