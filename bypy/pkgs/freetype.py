#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import os
import shutil

from bypy.constants import build_dir, iswindows
from bypy.utils import install_binaries, msbuild, replace_in_file, simple_build


def main(args):
    if iswindows:
        for f in (
            './devel/ftoption.h ./include/freetype/config/ftoption.h'.split()
        ):
            replace_in_file(
                f, 'FT_BEGIN_HEADER',
                'FT_BEGIN_HEADER\n#define FT_EXPORT(x) __declspec(dllexport) x\n#define FT_EXPORT_DEF(x) __declspec(dllexport) x\n'  # noqa
            )

        def build(static=False):
            conf = 'Release'
            if static:
                conf += ' Static'
            msbuild('builds/windows/vc2010/freetype.sln',
                    configuration=conf)

        # Build the static library
        # build(static=True)
        # install_binaries('objs/freetype.lib')
        # Build the dynamic library
        build()
        install_binaries('objs/freetype.dll', 'bin')
        install_binaries('objs/*/Release/*.lib')
        for f in glob.glob('objs/vc2010/*/freetype*MT.lib'):
            shutil.copy2(f, os.path.join(build_dir(), 'lib', 'freetype.lib'))
        shutil.copytree('include',
                        os.path.join(build_dir(), 'include', 'freetype2'))
        shutil.rmtree(
            os.path.join(build_dir(), 'include', 'freetype2', 'freetype',
                         'internal'))
    else:
        simple_build('--disable-dependency-tracking --disable-static')
