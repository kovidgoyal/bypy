#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re
import shutil

from bypy.constants import PREFIX, build_dir
from bypy.utils import ModifiedEnv, replace_in_file, simple_build, walk

needs_lipo = True


def main(args):
    # the makefile stupidly uses a comma as a separator for sed which breaks when there
    # are multiple entries being substituted
    replace_in_file('Makefile.am', re.compile(rb"'s,.+?'"), lambda m: m.group().replace(b',', b'`'))
    replace_in_file('Makefile.in', re.compile(rb"'s,.+?'"), lambda m: m.group().replace(b',', b'`'))
    with ModifiedEnv(
            FREETYPE_CFLAGS='-I%s/include/freetype2' % PREFIX,
            FREETYPE_LIBS='-L%s/lib -lfreetype -lz -lbz2' % PREFIX):
        simple_build(
            '--disable-dependency-tracking --disable-static --disable-docs'
            f' --with-expat={PREFIX} --with-add-fonts=/usr/share/fonts',
            library_path=True)
    for f in walk(os.path.join(build_dir(), 'etc')):
        if os.path.islink(f):
            x = os.path.realpath(f)
            os.unlink(f)
            shutil.copy2(x, f)
