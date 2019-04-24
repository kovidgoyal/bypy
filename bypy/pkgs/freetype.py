#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os
import shutil
import glob

from .constants import iswindows, is64bit, build_dir
from .utils import simple_build, replace_in_file, run, install_binaries


def main(args):
    if iswindows:
        for f in './devel/ftoption.h ./include/freetype/config/ftoption.h'.split():
            replace_in_file(f, 'FT_BEGIN_HEADER',
                            'FT_BEGIN_HEADER\n#define FT_EXPORT(x) __declspec(dllexport) x\n#define FT_EXPORT_DEF(x) __declspec(dllexport) x\n')
        vxproj = 'builds/windows/vc2010/freetype.vcxproj'
        # Upgrade the project file to build with VS 2015 devenv does not work,
        # probably because the Visual Studio Community edition is expired
        replace_in_file(vxproj, 'v100', 'v140')
        PL = 'x64' if is64bit else 'Win32'

        def build():
            run('msbuild.exe', 'builds/windows/vc2010/freetype.sln', '/t:Build', '/p:Platform=' + PL, '/p:Configuration=Release Multithreaded')

        # Build the static library
        build()
        install_binaries('objs/vc2010/*/freetype*MT.lib')
        shutil.copytree('include', os.path.join(build_dir(), 'include', 'freetype2'))
        shutil.rmtree(os.path.join(build_dir(), 'include', 'freetype2', 'freetype', 'internal'))
        # Build the dynamic library
        replace_in_file(vxproj, 'StaticLibrary', 'DynamicLibrary')
        build()
        install_binaries('objs/vc2010/*/freetype*MT.dll', 'bin')
        for f in glob.glob('objs/vc2010/*/freetype*MT.lib'):
            shutil.copy2(f, os.path.join(build_dir(), 'lib', 'freetype.lib'))
        # from .utils import run_shell
        # run_shell()
    else:
        simple_build('--disable-dependency-tracking --disable-static')
