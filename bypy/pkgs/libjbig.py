#!/usr/bin/env python
# License: GPLv3 Copyright: 2023, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import apply_patch, copy_headers, install_binaries, run


def main(args):
    apply_patch('jbigkit-2.1-shared_lib.patch', level=1)
    run('make')
    copy_headers('libjbig/*.h')
    install_binaries('libjbig/*.so*')
