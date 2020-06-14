#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import os
import re
import shutil

from bypy.constants import (LIBDIR, MAKEOPTS, PREFIX, build_dir, cygwin_paths,
                            is64bit, ismacos, iswindows)
from bypy.utils import (dos2unix, install_binaries, msbuild, replace_in_file,
                        run, simple_build, walk)


def solution_build():
    os.chdir('..')
    try:
        msbuild(r'source\allinone\allinone.sln', '/p:SkipUWP=true',
                PYTHONPATH=os.path.abspath(os.path.join('source', 'data')))
    except Exception:
        # the build fails while building the data/tools, which we dont need
        pass
    suffix = '64' if is64bit else ''
    dll_pat = f'bin{suffix}/icu*.dll'
    dlls = install_binaries(dll_pat, 'bin')
    if len(dlls) < 5:
        raise SystemExit(f'Failed to build ICU dlls in {dll_pat}')
    install_binaries(f'lib{suffix}/*.lib')
    shutil.copytree('include', os.path.join(build_dir(), 'include'))


def cygwin_build():
    for x in 'runConfigureICU configure config.sub config.guess'.split():
        dos2unix(x)
    replace_in_file(
        'configure',
        'PYTHONPATH="$srcdir/test/testdata:',
        'PYTHONPATH="$srcdir/test/testdata;')
    cyg_path = os.pathsep.join(cygwin_paths)
    bdir = build_dir().replace(os.sep, '/')
    run(
        'C:/cygwin64/bin/bash ./runConfigureICU Cygwin/MSVC'
        ' --disable-tools --disable-tests --disable-samples'
        f' --prefix {bdir}', append_to_path=cyg_path)
    # parallel builds fail, so no MAKEOPTS
    run('C:/cygwin64/bin/make', append_to_path=cyg_path)
    run('C:/cygwin64/bin/make install', append_to_path=cyg_path)
    for dll in glob.glob(os.path.join(build_dir(), 'lib', '*.dll')):
        if re.search(r'\d+', os.path.basename(dll)) is not None:
            os.rename(dll, os.path.join(
                build_dir(), 'bin', os.path.basename(dll)))
    for dll in glob.glob(os.path.join(build_dir(), 'lib', '*.dll')):
        os.remove(dll)


def main(args):
    os.chdir('source')

    if iswindows:
        solution_build()
    elif ismacos:
        run('./runConfigureICU MacOSX --disable-samples --prefix=' +
            build_dir())
        run('make ' + MAKEOPTS)
        run('make install')
    else:
        simple_build(
            '--prefix=/usr --sysconfdir=/etc --mandir=/usr/share/man'
            ' --sbindir=/usr/bin',
            install_args='DESTDIR=' + build_dir(),
            relocate_pkgconfig=False)
        usr = os.path.join(build_dir(), 'usr')
        os.rename(os.path.join(usr, 'include'),
                  os.path.join(build_dir(), 'include'))
        os.rename(os.path.join(usr, 'lib'), os.path.join(build_dir(), 'lib'))
        for path in walk(build_dir()):
            if path.endswith('.pc'):
                replace_in_file(path,
                                re.compile(br'^prefix\s*=\s*/usr', flags=re.M),
                                f'prefix={PREFIX}')
        shutil.rmtree(usr)


def install_name_change(name, is_dependency):
    bn = os.path.basename(name)
    if bn.startswith('libicu'):
        parts = bn.split('.')
        parts = parts[:2] + parts[
            -1:]  # We only want the major version in the install name
        name = LIBDIR + '/' + '.'.join(parts)
    return name
