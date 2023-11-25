#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import os
import shutil

from bypy.constants import (CFLAGS, LDFLAGS, MAKEOPTS, NMAKE, PERL, build_dir,
                            is64bit, ismacos, iswindows, current_build_arch)
from bypy.utils import run


needs_lipo = True


def main(args):
    if ismacos:
        arch = current_build_arch() or 'x86_64'
        run(
            f'./Configure darwin64-{arch}-cc shared enable-ec_nistp_64_gcc_128'
            f' no-ssl2 --prefix={build_dir()} --openssldir={build_dir()}')
        run('make ' + MAKEOPTS)
        run('make install_sw')
    elif iswindows:
        conf = f'{PERL} Configure VC-WIN32 enable-static-engine'.split()
        if is64bit:
            conf[2] = 'VC-WIN64A'
        else:
            conf.append('no-asm')
        conf.append('--prefix=' + build_dir())
        perl_path = os.path.dirname(PERL)
        run(*conf, prepend_to_path=perl_path)
        run(NMAKE, prepend_to_path=perl_path)
        run(NMAKE, 'test', prepend_to_path=perl_path)
        run(NMAKE, 'install', prepend_to_path=perl_path)
    else:
        optflags = ['enable-ec_nistp_64_gcc_128'] if is64bit else []
        # need --libdir=lib because on focal it becomes lib64 otherwise
        #
        # tests are very slow and flaky on ARM in QEMU
        #
        # need openssldir=/dev/null because Fedora uses an /etc/ssl that is
        # incompatible with upstream which completely breaks using openssl to
        # make connections. Fucking Linux distro wankers. When will these
        # idiots learn they ARE NOT COMPETENT TO PATCH UPSTREAM SOFTWARE. Keep
        # your grubby paws off other people's software.
        run('./config', '--prefix=/usr', '--libdir=lib',
            '--openssldir=/dev/null', 'shared', 'no-tests', 'zlib', '-Wa,--noexecstack',
            CFLAGS, LDFLAGS, *optflags)
        run('make ' + MAKEOPTS)
        run('make test', library_path=os.getcwd())
        run('make', 'DESTDIR={}'.format(build_dir()), 'install_sw')
        for x in 'bin lib include'.split():
            os.rename(
                os.path.join(build_dir(), 'usr', x),
                os.path.join(build_dir(), x))
        shutil.rmtree(glob.glob(os.path.join(
            build_dir(), 'lib', 'engines*'))[0])
