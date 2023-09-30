#!/usr/bin/env python
# License: GPLv3 Copyright: 2023, Kovid Goyal <kovid at kovidgoyal.net>


from bypy.utils import python_build, python_install, ModifiedEnv

def main(args):
    with ModifiedEnv(SKIP_CYTHON='1'):
        python_build(ignore_dependencies=True)  # we a re skipping cython
    python_install()
