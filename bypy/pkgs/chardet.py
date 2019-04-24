#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .utils import python_build, replace_in_file, python_install


def main(args):
    replace_in_file('setup.py', "setup_requires=['pytest-runner'],", '')
    python_build()
    python_install()
