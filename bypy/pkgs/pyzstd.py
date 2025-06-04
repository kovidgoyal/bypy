#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


import os

from bypy.constants import PREFIX
from bypy.utils import python_build, python_install, walk, build_dir, replace_in_file


def main(args):
    replace_in_file('setup.py',
                    "'include_dirs': [],    # .h directory",
                    f"""'include_dirs': [{repr(os.path.join(PREFIX, "include"))}],    # .h directory""")

    replace_in_file('setup.py',
                    "'library_dirs': [],    # .lib directory",
                    f"""'library_dirs': [{repr(os.path.join(PREFIX, "lib"))}],""")
    replace_in_file('src/__init__.py', 'from typing_extensions import deprecated', 'def deprecated(*a): return lambda f: f')
    python_build("--dynamic-link-zstd", ignore_dependencies=True)  # stupidly requires setuptools < 74 for python 3.9 support
    for f in walk(build_dir()):
        if os.path.basename(f) == 'c_pyzstd.py':
            q = os.path.join(os.path.dirname(f), '__init__.py')
            if not os.path.exists(q):
                open(q, 'w').close()
            break
    python_install()
