#!/usr/bin/env python
# License: GPLv3 Copyright: 2023, Kovid Goyal <kovid at kovidgoyal.net>

import re

from bypy.constants import UNIVERSAL_ARCHES, ismacos
from bypy.utils import (
    apply_patch, copy_headers, install_binaries, replace_in_file, run
)


def main(args):
    apply_patch('jbigkit-2.1-shared_lib.patch', level=1)
    if ismacos:
        replace_in_file('libjbig/Makefile',
            'libjbig.so.$(VERSION)', 'libjbig.$(VERSION).dylib')
        replace_in_file('libjbig/Makefile', '-Wl,-soname,$@', '')
        replace_in_file('libjbig/Makefile',
                        'libjbig85.so.$(VERSION)', 'libjbig85.$(VERSION).dylib')
        replace_in_file('libjbig/Makefile',
                        '%.so: %.so.$(VERSION)', '%.dylib: %.$(VERSION).dylib')
        replace_in_file('libjbig/Makefile',
                        re.compile('all:.+'), 'all: libjbig.dylib libjbig85.dylib')
        arches = ' '.join(f'-arch {x}' for x in UNIVERSAL_ARCHES)
        replace_in_file('libjbig/Makefile', 'CC = gcc', f'CC = gcc {arches}')
    run('make', 'lib')
    copy_headers('libjbig/*.h')
    if ismacos:
        install_binaries('libjbig/*.dylib')
    else:
        install_binaries('libjbig/*.so*')
