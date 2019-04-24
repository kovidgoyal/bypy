#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

import os
from .constants import iswindows, is64bit
from .utils import walk, run, install_binaries


def main(args):
    if iswindows:
        plat = 'x64' if is64bit else 'Win32'
        sln = r'jxrencoderdecoder\JXRDecApp_vc14.vcxproj'
        run('MSBuild.exe', sln, '/t:Build', '/p:Platform=' + plat, '/p:Configuration=Release', '/p:PlatformToolset=v140')

        def fname_map(x):
            return os.path.basename(x).rpartition('.')[0] + '-calibre.exe'

        for f in walk():
            if f.endswith('.exe'):
                install_binaries(f, 'bin', fname_map=fname_map)
    else:
        run('make', os.path.join(os.getcwd(), 'build/JxrDecApp'))
        install_binaries('build/JxrDecApp', 'bin')
