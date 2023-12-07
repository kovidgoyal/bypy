#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


import os

from bypy.constants import islinux
from bypy.utils import qt_build, require_ram, replace_in_file


def main(args):
    require_ram(24 if islinux else 8)
    conf = '-feature-qtwebengine-build -feature-qtwebengine-widgets-build'
    conf += ' -no-feature-qtwebengine-quick-build'
    if islinux:
        # use system ICU otherwise there is 10MB duplication
        conf += ' -webengine-icu'

        # fix building with libxml2 2.12
        replace_in_file(
            'src/3rdparty/chromium/third_party/blink/renderer/core/xml/xslt_processor.h',
            'static void ParseErrorFunc(void* user_data, xmlError*)',
            'static void ParseErrorFunc(void* user_data, const xmlError*)')
        replace_in_file(
            'src/3rdparty/chromium/third_party/blink/renderer/core/xml/xslt_processor_libxslt.cc',
            'void XSLTProcessor::ParseErrorFunc(void* user_data, xmlError* error) {',
            'void XSLTProcessor::ParseErrorFunc(void* user_data, const xmlError* error) {')

    qt_build(conf, for_webengine=True)


def is_ok_to_check_universal_arches(x):
    return os.path.basename(x) not in ('gn',)
