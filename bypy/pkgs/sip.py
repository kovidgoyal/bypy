#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import (MAKEOPTS, NMAKE, PREFIX, PYTHON, build_dir,
                            ismacos, iswindows)
from bypy.utils import replace_in_file, run


def main(args):
    b = build_dir()
    if ismacos:
        b = os.path.join(b, 'python/Python.framework/Versions/2.7')
    elif iswindows:
        b = os.path.join(b, 'private', 'python')
    cmd = [
        PYTHON, 'configure.py', '--no-pyi',
        '--sip-module=PyQt5.sip',
        '--bindir=%s/bin' % build_dir()]
    sp = 'Lib' if iswindows else 'lib/python2.7'
    inc = 'include' if iswindows else 'include/python2.7'
    cmd += ['--destdir=%s/%s/site-packages' % (b, sp),
            '--sipdir=%s/share/sip' % b,
            '--incdir=%s/%s' % (b, inc)]
    run(*cmd, library_path=True)
    if iswindows:
        run(f'"{NMAKE}"'), run(f'"{NMAKE}" install')
    else:
        run('make ' + MAKEOPTS)
        run('make install', library_path=True)
    q, r = build_dir(), PREFIX
    if iswindows:
        q = q.replace(os.sep, os.sep + os.sep)
        r = r.replace(os.sep, os.sep + os.sep)
    p = 'Lib' if iswindows else 'lib/python2.7'
    replace_in_file(os.path.join(b, p, 'site-packages/sipconfig.py'), q, r)
