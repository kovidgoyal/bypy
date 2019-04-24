#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os
import shutil

from .constants import is64bit, CFLAGS, LDFLAGS, MAKEOPTS, isosx, build_dir, iswindows
from .utils import run


def main(args):
    if isosx:
        run('sh ./Configure darwin64-x86_64-cc shared enable-ec_nistp_64_gcc_128 no-ssl2 --openssldir=' + build_dir())
        run('make ' + MAKEOPTS)
        run('make install')
    elif iswindows:
        conf = 'perl Configure VC-WIN32 enable-static-engine'.split()
        if is64bit:
            conf[2] = 'VC-WIN64A'
        else:
            conf.append('no-asm')
        conf.append('--prefix=' + build_dir())
        run(*conf)
        bat = 'ms\\do_win64a.bat' if is64bit else 'ms\\do_ms.bat'
        run(bat)
        run('nmake -f ms\\ntdll.mak')
        run('nmake -f ms\\ntdll.mak test')
        run('nmake -f ms\\ntdll.mak install')
    else:
        optflags = ['enable-ec_nistp_64_gcc_128'] if is64bit else []
        run('./config', '--prefix=/usr', '--openssldir=/etc/ssl', 'shared',
            'zlib', '-Wa,--noexecstack', CFLAGS, LDFLAGS, *optflags)
        run('make ' + MAKEOPTS)
        run('make test', library_path=os.getcwd())
        run('make', 'INSTALL_PREFIX={}'.format(build_dir()), 'install_sw')
        for x in 'bin lib include'.split():
            os.rename(os.path.join(build_dir(), 'usr', x), os.path.join(build_dir(), x))
        shutil.rmtree(os.path.join(build_dir(), 'lib', 'engines'))
