#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import re

from bypy.utils import python_build, python_install, replace_in_file


def main(args):
    replace_in_file('_fsevents.c', re.compile(r'if \(! PyEval_ThreadsInitialized.+?\}', re.DOTALL), '')
    python_build()
    python_install()
