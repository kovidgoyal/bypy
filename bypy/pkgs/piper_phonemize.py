#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>


import os
from bypy.constants import build_dir, PREFIX
from bypy.utils import cmake_build, replace_in_file

def main(args):
    replace_in_file('CMakeLists.txt', '${ONNXRUNTIME_DIR}/lib', '${ONNXRUNTIME_DIR}')
    cmake_build(
        override_prefix=os.path.join(build_dir(), 'piper-phonemize'), relocate_pkgconfig=False,
        CMAKE_VERBOSE_MAKEFILE='ON',
        ONNXRUNTIME_DIR=os.path.join(PREFIX, 'onnx').replace(os.sep, '/'),
        ESPEAK_NG_DIR=os.path.join(PREFIX, 'espeak').replace(os.sep, '/'),
    )
