#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import shutil

from bypy.constants import (CFLAGS, LDFLAGS, LIBDIR, MAKEOPTS, NMAKE, PREFIX,
                            build_dir, islinux, ismacos, iswindows)
from bypy.utils import replace_in_file, run, run_shell, apply_patch


def main(args):
    # https://bugreports.qt.io/browse/QTBUG-87320
    replace_in_file(
        'src/gui/image/qimage_conversions.cpp',
        'segments <= 1 ||',
        '!threadPool || segments <= 1 ||'
    )
    replace_in_file(
        'src/gui/image/qimage_conversions.cpp',
        'segments > 1 &&',
        'threadPool && segments > 1 &&'
    )
    # https://bugreports.qt.io/browse/QTBUG-86822
    replace_in_file(
        'src/plugins/platforms/cocoa/qcocoadrag.mm',
        'int(dragBoard.pasteboardItems.count) == 1 &&',
        ''
    )
    # https://bugreports.qt.io/browse/QTBUG-86604
    apply_patch('qtbug-86604.patch', level=1)

    if islinux:
        # We disable loading of bearer plugins because many distros ship with
        # broken bearer plugins that cause hangs.  At least, this was the case
        # in Qt 4.x Dont know if it is still true for Qt 5 but since we dont
        # need bearers anyway, it cant hurt.
        replace_in_file(
            'src/network/bearer/qnetworkconfigmanager_p.cpp',
            b'/bearer"', b'/bearer-disabled-by-kovid"')
        # Change pointing_hand to hand2, see
        # https://bugreports.qt.io/browse/QTBUG-41151
        replace_in_file('src/plugins/platforms/xcb/qxcbcursor.cpp',
                        'pointing_hand"', 'hand2"')
        # Fix for calibre flatpak runtime directory detection
        # https://github.com/containers/bubblewrap/issues/346
        apply_patch('patch_qtbase-revert-correct-handling-for-xdg-runtime-dir.patch', level=1)
        # Fixes for calibre flatpak that will be part of QT 5.15.2 release
        apply_patch('open-file-portal-writable.patch', level=1)
        apply_patch('qtbase-properly-fix-dangling-pointer.patch', level=1)
    if iswindows or islinux:
        # Let Qt setup its paths based on runtime location
        # this is needed because we want Qt to be able to
        # find its plugins etc before QApplication is constructed
        replace_in_file(
            'src/corelib/global/qlibraryinfo.cpp',
            '= getPrefix',
            '= getenv("CALIBRE_QT_PREFIX") ?'
            ' getenv("CALIBRE_QT_PREFIX") : getPrefix')
    if iswindows:
        # Enable loading of DLLs from the bin directory
        replace_in_file(
            'src/corelib/global/qlibraryinfo.cpp',
            '{ "Libraries", "lib" }',
            '{ "Libraries", "bin" }'
        )
        replace_in_file(
            'src/corelib/plugin/qsystemlibrary.cpp',
            'searchOrder << QFileInfo(qAppFileName()).path();',
            'searchOrder << (QFileInfo(qAppFileName()).path()'
            r".replace(QLatin1Char('/'), QLatin1Char('\\'))"
            r'+ QString::fromLatin1("\\app\\bin\\"));')
    cflags, ldflags = CFLAGS, LDFLAGS
    if ismacos:
        ldflags = '-L' + LIBDIR
    os.mkdir('build'), os.chdir('build')
    configure = os.path.abspath(
        '..\\configure.bat') if iswindows else '../configure'
    conf = configure + (
        ' -v -silent -opensource -confirm-license -prefix {}/qt -release'
        ' -nomake examples -nomake tests -no-sql-odbc -no-sql-psql'
        ' -icu -qt-harfbuzz -qt-doubleconversion').format(build_dir())
    if islinux:
        # Gold linker is needed for Qt 5.13.0 because of
        # https://bugreports.qt.io/browse/QTBUG-76196
        conf += (' -bundled-xcb-xinput -xcb -glib -openssl -qt-pcre'
                 ' -xkbcommon -libinput -linker gold')
    elif ismacos:
        conf += ' -no-pkg-config -framework -no-openssl -securetransport'
        ' -no-freetype -no-fontconfig '
    elif iswindows:
        # Qt links incorrectly against libpng and libjpeg, so use the bundled
        # copy Use dynamic OpenGl, as per:
        # https://doc.qt.io/qt-5/windows-requirements.html#dynamically-loading-graphics-drivers
        conf += (' -openssl -directwrite -ltcg -mp'
                 ' -no-plugin-manifests -no-freetype -no-fontconfig'
                 ' -qt-libpng -qt-libjpeg ')
        # The following config items are not supported on windows
        conf = conf.replace('-v -silent ', '-v ')
        cflags = '-I {}/include'.format(PREFIX).replace(os.sep, '/')
        ldflags = '-L {}/lib'.format(PREFIX).replace(os.sep, '/')
    conf += ' ' + cflags + ' ' + ldflags
    run(conf, library_path=True)
    # run_shell()
    run_shell
    if iswindows:
        run(f'"{NMAKE}"', append_to_path=f'{PREFIX}/private/gnuwin32/bin')
        run(f'"{NMAKE}" install')
        shutil.copy2('../src/3rdparty/sqlite/sqlite3.c',
                     os.path.join(build_dir(), 'qt'))
    else:
        run('make ' + MAKEOPTS, library_path=True)
        run('make install')
    with open(os.path.join(build_dir(), 'qt', 'bin', 'qt.conf'), 'wb') as f:
        f.write(b"[Paths]\nPrefix = ..\n")


def modify_exclude_extensions(extensions):
    extensions.discard('cpp')
