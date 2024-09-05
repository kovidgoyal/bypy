#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>


import glob
import os
import re
import shutil

from bypy.constants import PREFIX, build_dir, ismacos, iswindows
from bypy.utils import change_lib_names, cmake_build, copy_binaries, read_lib_names, replace_in_file


def main(args):
    dest = os.path.join(build_dir(), 'piper')
    if iswindows:
        # For some reason the linker fails to read spdlog.lib even though it
        # exists and is on LIBPATH and linking succeeds without it, so remove it
        replace_in_file('CMakeLists.txt', re.compile(r'^  spdlog\b', re.M), '')
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
    elif iswindows:
        pass
    else:
        for x in os.scandir(dest):
            if '.so.' in x.name and not x.is_symlink():
                os.chmod(x.path, 0o755)


def copy_piper_dir(src, dest):
    print('Copying piper...')
    src = os.path.join(src, 'piper')
    dest = os.path.join(dest, 'piper')
    copy_binaries(os.path.join(src, 'lib*'), dest)
    copy_binaries(os.path.join(src, 'piper*'), dest)
    shutil.copytree(os.path.join(src, 'espeak-ng-data'), os.path.join(dest, 'espeak-ng-data'))
