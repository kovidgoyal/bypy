#!/usr/bin/env python
# License: GPLv3 Copyright: 2023, Kovid Goyal <kovid at kovidgoyal.net>


from bypy.utils import python_build, python_install

def main(args):
    python_build(ignore_dependencies=True)  # it states it depends on cython but doesnt actually when biulding published sources
    python_install()
