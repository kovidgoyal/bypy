#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import CMAKE, PREFIX, PYTHON, current_build_arch, build_dir, ismacos, iswindows
from bypy.utils import copy_headers, install_binaries, replace_in_file, run, run_shell

run_shell
# sadly putting both arches in CMAKE_OSX_ARCHITECTURES caused build failures, so we lipo, sigh
needs_lipo=True
add_directml=False


def main(args):
    build_sh = 'build.bat' if iswindows else './build.sh'
    cmdline = f'{build_sh} --config Release --build_shared_lib --parallel --compile_no_warning_as_error --skip_submodule_sync --skip_tests'
    kw = {}
    if ismacos:
        if current_build_arch():
            cmdline += f' --cmake_extra_defines CMAKE_OSX_ARCHITECTURES={current_build_arch()}'
        kw['append_to_path'] = os.path.dirname(CMAKE)
        kw['prepend_to_path'] = os.path.dirname(PYTHON)  # onnx build script requires python >= 3.10
    elif iswindows:
        if add_directml:
            cmdline += ' --use_dml'
        kw['append_to_path'] = os.path.dirname(PYTHON)
        # The logic for setting the Visual Studio cmake generator is completely broken, so just let cmake pick for us,
        # which works since we have only one VS install.
        # Maybe use --cmake_generator Ninja in the future
        replace_in_file('tools/ci_build/build.py', '"-T", toolset, "-G", args.cmake_generator', '')
    else:
        # noexecstack is needed because some sub module dep of onnx causes the
        # find .so to have its stack marked executable which prevents it from
        # loading on most Linux systems.
        cmdline += f' --allow_running_as_root --cmake_extra_defines CMAKE_SYSTEM_PREFIX_PATH={PREFIX} CMAKE_SHARED_LINKER_FLAGS=-Wl,-z,noexecstack'
    run(cmdline, **kw)
    # run_shell()
    copy_headers('include/onnxruntime/core/session/*.h', 'include/onnxruntime')
    copy_headers('include/onnxruntime/core/providers/cpu/*.h', 'include/onnxruntime')
    copy_headers('include/onnxruntime/core/framework/provider_options.h', 'include/onnxruntime')
    if ismacos:
        install_binaries('build/*/Release/libonnxruntime*.dylib')
    elif iswindows:
        install_binaries('build/*/Release/Release/onnxruntime*.dll')
        if add_directml:
            install_binaries('build/*/Release/Release/DirectML.dll')
        install_binaries('build/*/Release/Release/onnxruntime*.lib')
    else:
        copy_headers('build/*/Release/*.pc', 'lib/pkgconfig')
        replace_in_file(os.path.join(build_dir(), 'lib/pkgconfig/libonnxruntime.pc'), '/usr/local', PREFIX)
        install_binaries('build/*/Release/libonnxruntime.so*')
