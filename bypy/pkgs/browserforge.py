#!/usr/bin/env python
# License: GPLv3 Copyright: 2026, Kovid Goyal <kovid at kovidgoyal.net>


import os

from bypy.utils import build_dir, python_build, python_install, walk


def main(args):
    python_build()
    for f in walk(build_dir()):
        if os.path.basename(os.path.dirname(f)) == "browserforge":
            q = os.path.join(os.path.dirname(f), "__init__.py")
            if not os.path.exists(q):
                open(q, "w").close()
            break
    python_install()
