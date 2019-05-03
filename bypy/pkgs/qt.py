#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import os
import shutil

from bypy.constants import (CFLAGS, LDFLAGS, LIBDIR, MAKEOPTS, PREFIX,
                            build_dir, islinux, ismacos, iswindows)
from bypy.utils import (ModifiedEnv, current_env, replace_in_file, run,
                        run_shell)


def main(args):
    if islinux:
        # We disable loading of bearer plugins because many distros ship with
        # broken bearer plugins that cause hangs.  At least, this was the case
        # in Qt 4.x Dont know if it is still true for Qt 5 but since we dont
        # need bearers anyway, it cant hurt.
        replace_in_file(
            'qtbase/src/network/bearer/qnetworkconfigmanager_p.cpp',
            b'/bearer"', b'/bearer-disabled-by-kovid"')
        # Change pointing_hand to hand2, see
        # https://bugreports.qt.io/browse/QTBUG-41151
        replace_in_file('qtbase/src/plugins/platforms/xcb/qxcbcursor.cpp',
                        'pointing_hand"', 'hand2"')
    elif iswindows:
        # Enable loading of DLLs from the DLLs directory
        replace_in_file(
            'qtbase/src/corelib/plugin/qsystemlibrary.cpp',
            'searchOrder << QFileInfo(qAppFileName()).path();',
            'searchOrder << (QFileInfo(qAppFileName()).path()'
            r".replace(QLatin1Char('/'), QLatin1Char('\\'))"
            r'+ QString::fromLatin1("\\app\\DLLs\\"));'
        )
    cflags, ldflags = CFLAGS, LDFLAGS
    if ismacos:
        ldflags = '-L' + LIBDIR
    os.mkdir('build'), os.chdir('build')
    configure = os.path.abspath(
        '..\\configure.bat') if iswindows else '../configure'
    # Slim down Qt
    # For the list of modules and their dependencies, see .gitmodules
    skip_modules = set('''\
        qtactiveqt qtscript qttools qtxmlpatterns qttranslations qtdoc
        qtrepotools qtqa qtsystems qtfeedback qtdocgallery
        qtpim qtconnectivity qt3d qtgraphicaleffects qtquickcontrols
        qtserialbus qtserialport qtquickcontrols2 qtcanvas3d qtpurchasing
        qtcharts qtdatavis3d qtvirtualkeyboard qtgamepad qtscxml qtspeech
        qtremoteobjects qtwebglplugin
    '''.split())
    conf = configure + (
        ' -v -silent -opensource -confirm-license -prefix {}/qt -release'
        ' -nomake examples -nomake tests -no-sql-odbc -no-sql-psql'
        ' -icu -qt-harfbuzz -qt-doubleconversion').format(build_dir())
    if islinux:
        conf += (
            ' -qt-xcb -glib -openssl -qt-pcre -xkbcommon -libinput'
        )
    elif ismacos:
        conf += ' -no-pkg-config -framework -no-openssl -securetransport'
        ' -no-freetype -no-fontconfig '
    elif iswindows:
        # Qt links incorrectly against libpng and libjpeg, so use the bundled
        # copy Use dynamic OpenGl, as per:
        # https://doc.qt.io/qt-5/windows-requirements.html#dynamically-loading-graphics-drivers
        conf += (
            ' -openssl -directwrite -ltcg -platform win32-msvc2015 -mp'
            ' -no-plugin-manifests -no-freetype -no-fontconfig'
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
        with ModifiedEnv(PATH=os.path.abspath('../gnuwin32/bin') + os.pathsep +
                         current_env()['PATH']):
            run('nmake')
        run('nmake install')
        shutil.copy2('../qtbase/src/3rdparty/sqlite/sqlite3.c',
                     os.path.join(build_dir(), 'qt'))
        shutil.copytree('../gnuwin32',
                        os.path.join(build_dir(), 'qt', 'gnuwin32'))
    else:
        run('make ' + MAKEOPTS, library_path=True)
        run('make install')
    with open(os.path.join(build_dir(), 'qt', 'bin', 'qt.conf'), 'wb') as f:
        f.write(b"[Paths]\nPrefix = ..\n")
    # for some reason these two files are not installed by make install as of
    # Qt 5.12.3
    os.chdir('..')
    for cpp in glob.glob(os.path.join(
        'qtbase', 'mkspecs', 'features', 'data', '*.cpp')
    ):
        shutil.copy2(cpp, os.path.join(
            build_dir(), 'qt', 'mkspecs', 'features', 'data',
            os.path.basename(cpp)))
