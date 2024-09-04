#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>


import os
from bypy.constants import build_dir, PREFIX
from bypy.utils import cmake_build

def main(args):
    dest = os.path.join(build_dir(), 'piper')
    cmake_build(
        override_prefix=dest, relocate_pkgconfig=False,
        CMAKE_VERBOSE_MAKEFILE='ON',
        PIPER_PHONEMIZE_DIR=os.path.join(PREFIX, 'piper-phonemize').replace(os.sep, '/'),
    )
    for x in os.scandir(dest):
        if '.so.' in x.name and not x.is_symlink():
            os.chmod(x.path, 0o755)
