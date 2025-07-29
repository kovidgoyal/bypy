#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re

from bypy.constants import CMAKE, PREFIX, PYTHON, UNIVERSAL_ARCHES, build_dir, ismacos, iswindows
from bypy.utils import copy_headers, install_binaries, replace_in_file, run, run_shell

run_shell


def main(args):
    build_sh = 'build.bat' if iswindows else './build.sh'
    cmdline = f'{build_sh} --config Release --build_shared_lib --parallel --compile_no_warning_as_error --skip_submodule_sync --skip_tests'
    kw = {}
    if ismacos:
        arches = ';'.join(UNIVERSAL_ARCHES)
        cmdline += f' --cmake_extra_defines CMAKE_OSX_ARCHITECTURES={arches} CMAKE_VERBOSE_MAKEFILE=ON'
        kw['append_to_path'] = os.path.dirname(CMAKE)
        kw['prepend_to_path'] = os.path.dirname(PYTHON)  # onnx build script requires python >= 3.10
    elif iswindows:
        replace_in_file('tools/ci_build/build.py', 'target_arch = platform.machine()', 'target_arch = platform.machine().upper()')
        kw['append_to_path'] = os.path.dirname(PYTHON)
        # Visual Studio 2022 ships with ancient CMake, but we dont actually
        # need updated cmake with one C++ 23 patch
        replace_in_file('cmake/CMakeLists.txt', re.compile(r'cmake_minimum_required.+'), '')
        replace_in_file('cmake/onnxruntime_common.cmake', re.compile(r'if.+cxx_std_23.+'), 'if(FALSE)')
    else:
        cmdline += f' --allow_running_as_root --cmake_extra_defines CMAKE_SYSTEM_PREFIX_PATH={PREFIX} CMAKE_SHARED_LINKER_FLAGS=-Wl,-z,noexecstack'
    run(cmdline, **kw)
    # run_shell()
    copy_headers('include/onnxruntime/core/session/*.h', 'include/onnxruntime')
    copy_headers('include/onnxruntime/core/providers/cpu/*.h', 'include/onnxruntime')
    copy_headers('include/onnxruntime/core/framework/provider_options.h', 'include/onnxruntime')
    if ismacos:
        install_binaries('build/*/Release/libonnxruntime*.dylib')
    elif iswindows:
        install_binaries('build/Windows/Release/Release/onnxruntime*.dll')
        install_binaries('build/Windows/Release/Release/onnxruntime*.lib')
    else:
        copy_headers('build/*/Release/*.pc', 'lib/pkgconfig')
        replace_in_file(os.path.join(build_dir(), 'lib/pkgconfig/libonnxruntime.pc'), '/usr/local', PREFIX)
        install_binaries('build/*/Release/libonnxruntime.so*')
