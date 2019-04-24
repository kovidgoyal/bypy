#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os
import shutil

from .constants import CFLAGS, LDFLAGS, MAKEOPTS, build_dir, isosx, islinux, LIBDIR, iswindows, PREFIX
from .utils import apply_patch, run, run_shell, replace_in_file, ModifiedEnv, current_env


def main(args):
    if islinux:
        # We disable loading of bearer plugins because many distros ship with
        # broken bearer plugins that cause hangs.  At least, this was the case in
        # Qt 4.x Dont know if it is still true for Qt 5 but since we dont need
        # bearers anyway, it cant hurt.
        replace_in_file('qtbase/src/network/bearer/qnetworkconfigmanager_p.cpp', b'/bearer"', b'/bearer-disabled-by-kovid"')
        # Change pointing_hand to hand2, see
        # https://bugreports.qt.io/browse/QTBUG-41151
        replace_in_file('qtbase/src/plugins/platforms/xcb/qxcbcursor.cpp', 'pointing_hand"', 'hand2"')
    elif iswindows:
        # Enable loading of DLLs from the DLLs directory
        replace_in_file(
            'qtbase/src/corelib/plugin/qsystemlibrary.cpp',
            'searchOrder << QFileInfo(qAppFileName()).path();',
            r'''searchOrder << (QFileInfo(qAppFileName()).path().replace(QLatin1Char('/'), QLatin1Char('\\')) + QString::fromLatin1("\\app\\DLLs\\"));''')
    cflags, ldflags = CFLAGS, LDFLAGS
    if isosx:
        apply_patch('fix_mojave_font_weights_in_qt_5.6.patch')
        ldflags = '-L' + LIBDIR
        # The following is needed as without it the Qt build system does not add the
        # necessary -stdlib=libc++ when linking. Probably, you can get rid of
        # this on newer OS X systems/newer Qt versions
        replace_in_file('qtbase/mkspecs/macx-clang/qmake.conf', 'MACOSX_DEPLOYMENT_TARGET = 10.7', 'MACOSX_DEPLOYMENT_TARGET = 10.9')
    os.mkdir('build'), os.chdir('build')
    configure = os.path.abspath('..\\configure.bat') if iswindows else '../configure'
    # Slim down Qt
    # For the list of modules and their dependencies, see .gitmodules
    skip_modules = (
        # To add web engine remove qtwebengine and qtwebview from this list
        'qtdeclarative qtactiveqt qtscript qttools qtxmlpatterns qttranslations qtdoc'
        ' qt3d qtgraphicaleffects qtquickcontrols qtquickcontrols2 qtwebengine qtwebview'
        ' qtcanvas3d'
    ).split()
    conf = configure + (
        ' -v -silent -opensource -confirm-license -prefix {}/qt -release -nomake examples -nomake tests'
        ' -no-sql-odbc -no-sql-psql -no-qml-debug -icu -qt-harfbuzz'
    ).format(build_dir())
    if islinux:
        # Ubuntu 12.04 has gcc 4.6.3 which does not support c++11
        conf += ' -qt-xcb -glib -openssl -gtkstyle -qt-pcre -c++std c++98'
    elif isosx:
        # Use c++11 rather than the newest available for maximum backwards
        # compat
        conf += ' -no-pkg-config -framework -no-openssl -securetransport -no-freetype -no-fontconfig -c++std c++11'
    elif iswindows:
        # Qt links incorrectly against libpng and libjpeg, so use the bundled copy
        # Use dynamic OpenGl, as per:
        # https://doc.qt.io/qt-5/windows-requirements.html#dynamically-loading-graphics-drivers
        conf += (' -openssl -directwrite -ltcg -platform win32-msvc2015 -mp -no-plugin-manifests -no-freetype -no-fontconfig'
                 ' -no-angle -opengl dynamic -qt-libpng -qt-libjpeg ')
        # The following config items are not supported on windows
        conf = conf.replace('-v -silent ', ' ')
        cflags = '-I {}/include'.format(PREFIX).replace(os.sep, '/')
        ldflags = '-L {}/lib'.format(PREFIX).replace(os.sep, '/')
    skip_modules = ' '.join('-skip ' + x for x in skip_modules)
    conf += ' ' + skip_modules + ' ' + cflags + ' ' + ldflags
    run(conf, library_path=True)
    # run_shell()
    run_shell
    if iswindows:
        with ModifiedEnv(PATH=os.path.abspath('../gnuwin32/bin') + os.pathsep + current_env()['PATH']):
            run('nmake')
        run('nmake install')
        shutil.copy2('../qtbase/src/3rdparty/sqlite/sqlite3.c', os.path.join(build_dir(), 'qt'))
        shutil.copytree('../gnuwin32', os.path.join(build_dir(), 'qt', 'gnuwin32'))
    else:
        run('make ' + MAKEOPTS, library_path=True)
        run('make install')
    with open(os.path.join(build_dir(), 'qt', 'bin', 'qt.conf'), 'wb') as f:
        f.write(b"[Paths]\nPrefix = ..\n")
