#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os
import re
import shutil

from .constants import MAKEOPTS, build_dir, iswindows, PREFIX, isosx
from .utils import walk, run, run_shell, replace_in_file, ModifiedEnv, current_env, apply_patch


def main(args):
    # Control font hinting
    apply_patch('webkit_control_hinting.patch', convert_line_endings=iswindows)
    # Do not build webkit2
    replace_in_file('Tools/qmake/mkspecs/features/configure.prf', 'build_webkit2 \\', '\\')
    if isosx:
        # Bug in qtwebkit, the OBJC API gets turned on if
        # MAC_OSX_DEPLOYMENT_TARGET >= 10.9 (which we do in the qt build)
        # However it is broken, so disable it explicitly here
        replace_in_file('Source/JavaScriptCore/API/JSBase.h', '#define JSC_OBJC_API_ENABLED (', '#define JSC_OBJC_API_ENABLED (0 && ')

    lp = os.path.join(PREFIX, 'qt', 'lib')
    bdir = os.path.join(build_dir(), 'qt')
    qmake = os.path.join(PREFIX, 'qt', 'bin', 'qmake')
    env = {}
    if iswindows:
        env['SQLITE3SRCDIR'] = os.path.join(PREFIX, 'qt')
        env['PATH'] = current_env()['PATH'] + os.pathsep + os.path.join(PREFIX, 'qt', 'gnuwin32', 'bin')
        # All that follows is to enable usage of libxml2/libxslt
        libxml2 = os.path.join(PREFIX, 'lib', 'libxml2.lib').replace(os.sep, '/')
        libxml2_inc = os.path.join(PREFIX, 'include', 'libxml2').replace(os.sep, '/')
        replace_in_file('Tools/qmake/config.tests/libxml2/libxml2.pro', re.compile(r'mac {.+}', re.DOTALL),
                        'LIBS += {}\nINCLUDEPATH += {}\nCONFIG += console'.format(
                        libxml2, libxml2_inc))
        replace_in_file('Tools/qmake/config.tests/libxslt/libxslt.pro', re.compile(r'mac {.+}', re.DOTALL),
                        'LIBS += {} {}\nINCLUDEPATH += {} {}\nCONFIG += console'.format(
                        libxml2, libxml2.replace('xml2', 'xslt'), libxml2_inc, os.path.join(PREFIX, 'include').replace(os.sep, '/')))
        replace_in_file('Source/WebCore/WebCore.pri', 'PKGCONFIG += libxslt libxml-2.0',
                        'LIBS += {} {}\nINCLUDEPATH += {} {}'.format(
                            libxml2, libxml2.replace('xml2', 'xslt'), libxml2_inc, os.path.join(PREFIX, 'include').replace(os.sep, '/')))
    os.mkdir('build'), os.chdir('build')
    with ModifiedEnv(**env):
        run(qmake, 'PREFIX=' + bdir.replace(os.sep, '/'), '..', library_path=lp)
        # run_shell()
        run_shell
        if iswindows:
            run('nmake')
            qt = os.path.join(PREFIX, 'qt')
            # There seems to be no way to get the qtwebkit build system to
            # output files to INSTALL_ROOT on windows. Also the makefile
            # requires the existing Qt installation to be present while running
            # nmake install. So we diff the filesystems to get the list of
            # files to install.
            before_files = {f: os.path.getmtime(f) for f in walk(qt)}
            run('nmake install')
            for f in walk(qt):
                mtime = os.path.getmtime(f)
                pmtime = before_files.get(f)
                if pmtime != mtime:
                    dest = os.path.join(bdir, os.path.relpath(f, qt))
                    try:
                        os.rename(f, dest)
                    except EnvironmentError:
                        os.makedirs(os.path.dirname(dest))
                        os.rename(f, dest)
        else:
            run('make ' + MAKEOPTS, library_path=lp)
            run('make INSTALL_ROOT=%s install' % bdir)
            idir = os.path.join(bdir, 'sw', 'sw', 'qt')
            for x in os.listdir(idir):
                os.rename(os.path.join(idir, x), os.path.join(bdir, x))
            shutil.rmtree(os.path.join(bdir, 'sw'))
