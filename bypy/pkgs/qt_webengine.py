#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


from bypy.constants import islinux, iswindows
from bypy.utils import qt_build, replace_in_file, apply_patch


def main(args):
    conf = '-feature-qtwebengine-build -feature-qtwebengine-widgets-build'
    conf += ' -no-feature-qtwebengine-quick-build'
    if islinux:
        # see https://bugs.launchpad.net/calibre/+bug/1939958
        apply_patch('crbug1213452.diff', level=1)
        # use system ICU otherwise there is 10MB duplication and we have to
        # make resources/icudtl.dat available in the application
        conf += ' -webengine-icu'

    if iswindows:
        # broken test for 64-bit ness needs to be disabled
        replace_in_file('configure.pri', 'ProgramW6432', 'PROGRAMFILES')
        # Needed for Qt 5.15.0 https://github.com/microsoft/vcpkg/issues/12477
        # replace_in_file(
        #     'src/3rdparty/chromium/third_party/perfetto/src/trace_processor/'
        #     'importers/systrace/systrace_trace_parser.cc',
        #     '#include <inttypes.h>',
        #     '#include <cctype>\n#include <inttypes.h>')
    qt_build(conf, for_webengine=True)
