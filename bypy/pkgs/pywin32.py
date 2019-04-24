#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os
import shutil

from .constants import is64bit, PYTHON, build_dir, SW, PREFIX
from .utils import run, replace_in_file


def main(args):
    replace_in_file('setup.py', 'self._want_assembly_kept = sys', 'self._want_assembly_kept = False and sys')
    run(PYTHON, 'setup.py', '-q', 'build', '--plat-name=' + ('win-amd64' if is64bit else 'win32'))
    run(PYTHON, 'setup.py', '-q', 'install', '--root', build_dir())
    os.rename(os.path.join(build_dir(), os.path.basename(SW), os.path.basename(PREFIX), 'private'), os.path.join(build_dir(), 'private'))
    shutil.rmtree(os.path.join(build_dir(), os.path.basename(SW)))
