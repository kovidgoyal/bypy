#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import (BIN, CMAKE, PREFIX, build_dir, islinux, ismacos,
                            iswindows)
from bypy.utils import (relocate_pkgconfig_files, replace_in_file, run,
                        run_shell)


def cmake(args):
    # Mapping of configure args to cmake directoves comes from the file
    # cmake/configure-cmake-mapping.md in the qtbase source code.
    cmake_defines = {
        'CMAKE_INSTALL_PREFIX': os.path.join(build_dir(), 'qt'),
        'QT_BUILD_EXAMPLES': 'FALSE',
        'QT_BUILD_TESTS': 'FALSE',
        'CMAKE_BUILD_TYPE': 'Release',
        'OPENSSL_ROOT_DIR': PREFIX,
        'ICU_ROOT': PREFIX,
        'CMAKE_SYSTEM_PREFIX_PATH': PREFIX,
        'INPUT_sql_odbc': 'no',
        'INPUT_sql_psql': 'no',
        'INPUT_icu': 'yes',
        'INPUT_harfbuzz': 'qt',
        'INPUT_doubleconversion': 'qt',
        'INPUT_pcre': 'qt',
    }
    if islinux:
        cmake_defines.update({
            'INPUT_bundled_xcb_xinput': 'yes',
            'INPUT_xcb': 'yes',
            'INPUT_glib': 'yes',
            'INPUT_openssl': 'linked',
            'INPUT_xkbcommon': 'yes',
            'INPUT_libinput': 'yes',
            # 'INPUT_linker': 'gold',
            'INPUT_pkg_config': 'yes',
            # 'INPUT_wflags': 'l,-rpath-link,/sw/sw/lib--',
        })
    os.mkdir('build'), os.chdir('build')
    cmd = [CMAKE] + [f'-D{k}={v}' for k, v in cmake_defines.items()] + [
        '-G', 'Ninja', '..']
    run(*cmd, library_path=True, append_to_path=BIN)
    run_shell  # ()
    if iswindows:
        run('cmake --build . --parallel',
            append_to_path=f'{PREFIX}/private/gnuwin32/bin')
    else:
        run('cmake --build . --parallel',
            library_path=True, append_to_path=BIN)
    run('cmake --install .')
    with open(os.path.join(build_dir(), 'qt', 'bin', 'qt.conf'), 'wb') as f:
        f.write(b"[Paths]\nPrefix = ..\n")


def main(args):
    if islinux:
        # Change pointing_hand to hand2, see
        # https://bugreports.qt.io/browse/QTBUG-41151
        replace_in_file('src/plugins/platforms/xcb/qxcbcursor.cpp',
                        'pointing_hand"', 'hand2"')
    if iswindows or islinux:
        # Let Qt setup its paths based on runtime location
        # this is needed because we want Qt to be able to
        # find its plugins etc before QApplication is constructed
        getenv = '_wgetenv' if iswindows else 'getenv'
        ff = 'fromWCharArray' if iswindows else 'fromUtf8'
        ev = 'L"CALIBRE_QT_PREFIX"' if iswindows else '"CALIBRE_QT_PREFIX"'
        replace_in_file(
            'src/corelib/global/qlibraryinfo.cpp',
            '= getPrefix',
            f'= {getenv}({ev}) ?'
            f' QString::{ff}({getenv}({ev})) : getPrefix')
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
    cmake(args)
    relocate_pkgconfig_files()
    # cflags, ldflags = CFLAGS, LDFLAGS
    # cmake_args = ''
    # if ismacos:
    #     ldflags = '-L' + LIBDIR
    # os.mkdir('build'), os.chdir('build')
    # configure = os.path.abspath(
    #     '..\\configure.bat') if iswindows else '../configure'
    # conf = configure + (
    #     ' -prefix {}/qt -release'
    #     ' -nomake examples -nomake tests -no-sql-odbc -no-sql-psql'
    #     ' -icu -qt-harfbuzz -qt-doubleconversion').format(build_dir())
    # if islinux:
    #     # Gold linker is needed for Qt 5.13.0 because of
    #     # https://bugreports.qt.io/browse/QTBUG-76196
    #     conf += (
    #         ' -bundled-xcb-xinput -xcb -glib -openssl -openssl-linked'
    #         ' -qt-pcre -xkbcommon -libinput -linker gold -pkg-config')
    #     cmake_args += f'-D OPENSSL_ROOT_DIR={PREFIX}'
    # elif ismacos:
    #     conf += ' -no-pkg-config -framework -no-openssl -securetransport'
    #     ' -no-freetype -no-fontconfig '
    # elif iswindows:
    #     # Qt links incorrectly against libpng and libjpeg, so use the bundled
    #     # copy Use dynamic OpenGl, as per:
    #     # https://doc.qt.io/qt-5/windows-requirements.html#dynamically-loading-graphics-drivers
    #     conf += (' -schannel -no-openssl -directwrite -ltcg -mp'
    #              ' -no-plugin-manifests -no-freetype -no-fontconfig'
    #              ' -qt-libpng -qt-libjpeg ')
    #     cflags = '-I {}/include'.format(PREFIX).replace(os.sep, '/')
    #     ldflags = '-L {}/lib'.format(PREFIX).replace(os.sep, '/')
    # conf += ' ' + cflags + ' ' + ldflags
    # if cmake_args:
    #     conf += f'-- {cmake_args}'
    # run(conf, library_path=True)
    # # run_shell()
    # run_shell
    # if iswindows:
    #     run('cmake --build . --parallel',
    #         append_to_path=f'{PREFIX}/private/gnuwin32/bin')
    #     run('cmake --install .')
    #     shutil.copy2('../src/3rdparty/sqlite/sqlite3.c',
    #                  os.path.join(build_dir(), 'qt'))
    # else:
    #     run('cmake --build . --parallel',
    #         library_path=True, append_to_path=BIN)
    #     run('cmake --install .')


def modify_exclude_extensions(extensions):
    extensions.discard('cpp')
