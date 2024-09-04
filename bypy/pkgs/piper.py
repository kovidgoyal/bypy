#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>


import glob
import os
import shutil

from bypy.constants import PREFIX, build_dir, ismacos
from bypy.utils import cmake_build, read_lib_names, change_lib_names


def main(args):
    dest = os.path.join(build_dir(), 'piper')
    cmake_build(
        override_prefix=dest, relocate_pkgconfig=False,
        CMAKE_VERBOSE_MAKEFILE='ON',
        PIPER_PHONEMIZE_DIR=os.path.join(PREFIX, 'piper-phonemize').replace(os.sep, '/'),
    )
    if ismacos:
        # Install needed dylibs and fix the dynamic link lookup info in them
        def chrpath(x):
            install_name, deps = read_lib_names(x)
            changes = []
            if x.endswith('.dylib'):
                changes.append((None, install_name.replace('@rpath', '@executable_path')))
            for d in deps:
                if '@rpath' in d:
                    changes.append((d, d.replace('@rpath', '@executable_path')))
            change_lib_names(x, changes)
        def cp(x):
            x = glob.glob(os.path.join(PREFIX, 'piper-phonemize', 'lib', x))[0]
            d = os.path.join(dest, os.path.basename(x))
            shutil.copy2(x, d)
            os.chmod(d, 0o755)
            chrpath(d)
        cp('libespeak-ng.?.dylib')
        cp('libpiper_phonemize.?.dylib')
        cp('libonnxruntime.?.*.?.dylib')
        for x in ('piper', 'piper_phonemize'):
            chrpath(os.path.join(dest, x))
    else:
        for x in os.scandir(dest):
            if '.so.' in x.name and not x.is_symlink():
                os.chmod(x.path, 0o755)
