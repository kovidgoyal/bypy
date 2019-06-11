#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
from bypy.constants import iswindows
from bypy.utils import walk, run, install_binaries, msbuild


def main(args):
    if iswindows:
        sln = r'jxrencoderdecoder\JXRDecApp_vc14.vcxproj'
        msbuild(sln)

        def fname_map(x):
            return os.path.basename(x).rpartition('.')[0] + '-calibre.exe'

        for f in walk():
            if f.endswith('.exe'):
                install_binaries(f, 'bin', fname_map=fname_map)
    else:
        run('make', os.path.join(os.getcwd(), 'build/JxrDecApp'))
        install_binaries('build/JxrDecApp', 'bin')
