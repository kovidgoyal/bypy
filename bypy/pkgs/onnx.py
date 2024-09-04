#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import CMAKE, PREFIX, UNIVERSAL_ARCHES, ismacos
from bypy.utils import copy_headers, install_binaries, run, run_shell

run_shell


def main(args):
    cmdline = './build.sh --config Release --build_shared_lib --parallel --compile_no_warning_as_error --skip_submodule_sync --skip_tests'
    kw = {}
    if ismacos:
        arches = ';'.join(UNIVERSAL_ARCHES)
        cmdline += f' --cmake_extra_defines CMAKE_OSX_ARCHITECTURES={arches} CMAKE_VERBOSE_MAKEFILE=ON'
        kw['append_to_path'] = os.path.dirname(CMAKE)
    else:
        cmdline += f' --allow_running_as_root --cmake_extra_defines CMAKE_SYSTEM_PREFIX_PATH={PREFIX}'
    run(cmdline, **kw)
    # run_shell()
    copy_headers('include/onnxruntime/core/session/*.h', 'onnx/include')
    copy_headers('include/onnxruntime/core/providers/cpu/*.h', 'onnx/include')
    copy_headers('include/onnxruntime/core/framework/provider_options.h', 'onnx/include')
    if ismacos:
        install_binaries('build/*/Release/libonnxruntime*.dylib', 'onnx')
    else:
        install_binaries('build/*/Release/libonnxruntime.so*', 'onnx')
