#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import ismacos, UNIVERSAL_ARCHES
from bypy.utils import run, run_shell, install_binaries, copy_headers


run_shell


def main(args):
    cmdline = './build.sh --config Release --build_shared_lib --parallel --compile_no_warning_as_error --skip_submodule_sync --skip_tests'
    if ismacos:
        arches = ';'.join(UNIVERSAL_ARCHES)
        cmdline += f' --cmake_extra_defines CMAKE_OSX_ARCHITECTURES="{arches}"'
    run(cmdline)
    # run_shell()
    copy_headers('include/onnxruntime/core/session/*.h', 'onnx/include')
    copy_headers('include/onnxruntime/core/providers/cpu/*.h', 'onnx/include')
    copy_headers('include/onnxruntime/core/framework/provider_options.h', 'onnx/include')
    install_binaries('build/*/Release/libonnxruntime.so*', 'onnx')
