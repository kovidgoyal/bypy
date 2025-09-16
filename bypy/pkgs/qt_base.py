#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import BIN, CMAKE, PERL, PREFIX, UNIVERSAL_ARCHES, build_dir, currently_building_dep, islinux, ismacos, iswindows
from bypy.utils import apply_patch, relocate_pkgconfig_files, replace_in_file, run, run_shell


apply_patch


def cmake(args):
    # Mapping of configure args to cmake directives comes from the file
    # cmake/configure-cmake-mapping.md in the qtbase source code.
    cmake_defines = {
        'CMAKE_INSTALL_PREFIX': os.path.join(build_dir(), 'qt'),
        'CMAKE_SYSTEM_PREFIX_PATH': PREFIX,
        'CMAKE_BUILD_TYPE': 'Release',
        'CMAKE_INTERPROCEDURAL_OPTIMIZATION': 'ON',  # LTO build
        'QT_BUILD_EXAMPLES': 'FALSE',
        'QT_BUILD_TESTS': 'FALSE',
        'OPENSSL_ROOT_DIR': PREFIX,
        'ICU_ROOT': PREFIX,
        'ZLIB_ROOT': PREFIX,
        'JPEG_ROOT': PREFIX,
        'PNG_ROOT': PREFIX,
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
    if ismacos:
        apply_patch('qtbug-134073.patch', level=0)
        if len(UNIVERSAL_ARCHES) > 1:
            cmake_defines['CMAKE_OSX_ARCHITECTURES'] = ';'.join(UNIVERSAL_ARCHES)
        cmake_defines.update({
            'FEATURE_framework': 'ON',
            'FEATURE_pkg_config': 'OFF',
            'INPUT_openssl': 'no',
            'FEATURE_securetransport': 'ON',
            'FEATURE_fontconfig': 'OFF',
        })
    if iswindows:
        cmake_defines.update({
            'INPUT_openssl': 'no',
            'FEATURE_pkg_config': 'OFF',
            'FEATURE_schannel': 'ON',
            'FEATURE_fontconfig': 'OFF',
        })
        # allow overriding Qt's notion of the cache dir which is used by
        # QWebEngineProfile
        replace_in_file(
            './src/corelib/io/qstandardpaths_win.cpp', 'case CacheLocation:',
            'case CacheLocation: {'
            ' const wchar_t *cq = _wgetenv(L"CALIBRE_QT_CACHE_LOCATION");'
            ' if (cq) return QString::fromWCharArray(cq); }')
    os.mkdir('build'), os.chdir('build')
    cmd = [CMAKE] + [f'-D{k}={v}' for k, v in cmake_defines.items()] + [
        '-G', 'Ninja', '..']
    if iswindows:
        run(*cmd, library_path=True, append_to_path=BIN,
            prepend_to_path=os.path.dirname(PERL))
        run_shell  # ()
        run(CMAKE, '--build', '.', '--parallel',
            prepend_to_path=os.path.dirname(PERL),
            append_to_path=f'{PREFIX}/private/gnuwin32/bin')
    else:
        run(*cmd, library_path=True, append_to_path=BIN)
        run_shell  # ()
        run(CMAKE, '--build', '.', '--parallel',
            library_path=True, append_to_path=BIN)
    run(CMAKE, '--install', '.')
    with open(os.path.join(build_dir(), 'qt', 'bin', 'qt.conf'), 'wb') as f:
        f.write(b"[Paths]\nPrefix = ..\n")
        if iswindows:
            # this is needed for qmake as otherwise qmake sets QT_INSTALL_LIBS
            # to bin which breaks building of PyQt. Hopefully if and when PyQt
            # moves off qmake this can be removed
            f.write(b'Libraries = lib\n')


def main(args):
    if islinux:
        # Change pointing_hand to hand2, see
        # https://bugreports.qt.io/browse/QTBUG-41151
        replace_in_file('src/plugins/platforms/xcb/qxcbcursor.cpp',
                        'pointing_hand"', 'hand2"')
        # Get QProcess to work with QEMU user mode
        # https://bugreports.qt.io/browse/QTBUG-98951
        replace_in_file(
            'src/corelib/io/qprocess_unix.cpp',
            '#if defined(Q_OS_LINUX) && !QT_CONFIG(forkfd_pidfd)',
            'if (getenv("QT_QPROCESS_NO_VFORK")) return false;\n'
            '#if defined(Q_OS_LINUX) && !QT_CONFIG(forkfd_pidfd)'
        )
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
            '"Libraries", "lib"',
            '"Libraries", "bin"'
        )
        replace_in_file(
            'src/corelib/plugin/qsystemlibrary.cpp',
            'searchOrder << QFileInfo(qAppFileName()).path();',
            'searchOrder << (QFileInfo(qAppFileName()).path()'
            r".replace(QLatin1Char('/'), QLatin1Char('\\'))"
            r'+ QString::fromLatin1("\\app\\bin\\"));')
    cmake(args)
    relocate_pkgconfig_files()


def modify_exclude_extensions(extensions):
    extensions.discard('cpp')


def modify_excludes(excludes):
    if currently_building_dep().name == 'qt-declarative':
        # qt-declarative puts artifacts needed for modules that depnd on it to
        # build in the test directory. Bloody lunacy.
        excludes.discard('test')
