#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import shutil

from bypy.constants import iswindows
from bypy.utils import copy_headers, install_binaries, msbuild, simple_build


def main(args):
    if iswindows:
        shutil.rmtree('lib'), shutil.rmtree('lib64')
        os.mkdir('lib'), os.mkdir('lib64')
        msbuild('libiconv.vcxproj')
        copy_headers('include/iconv.h')
        install_binaries('./lib*/libiconv.dll', 'bin')
        install_binaries('./lib*/libiconv.lib', 'lib')
        # from bypy.utils import run_shell
        # run_shell()
    else:
        simple_build(
            '--disable-dependency-tracking --disable-static --enable-shared')


def filter_pkg(parts):
    return 'locale' in parts
