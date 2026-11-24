#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import shutil

from bypy.constants import build_dir
from bypy.utils import meson_build, walk

needs_lipo = True


def main(args):
    meson_build(
        '--wrap-mode=nofallback',
        library_path=True,
        doc='disabled', nls='disabled', tests='disabled',
        **{
            'cache-build': 'disabled',
            'xml-backend': 'expat',
            'additional-fonts-dirs': '/usr/share/fonts',
        })
    for f in walk(os.path.join(build_dir(), 'etc')):
        if os.path.islink(f):
            x = os.path.realpath(f)
            os.unlink(f)
            shutil.copy2(x, f)
