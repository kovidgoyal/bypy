#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import cmake_build, replace_in_file


def main(args):
    # Linux distros have libtiff but calibre does not bundle libtiff, we dont
    # want libpodofo to link against the system libtiff
    replace_in_file('CMakeLists.txt', 'if(TIFF_FOUND)', 'if(TIFF_FOUND_DISABLED)')

    # Patches to build with newer versions of libxml2
    # https://github.com/podofo/podofo/commit/d470a0a2ad423042c29db08ba13170f42d8806cf
    replace_in_file('src/podofo/private/XmlUtils.h', '#include <libxml/tree.h>', '#include <libxml/tree.h>\n#include <libxml/xmlerror.h>')
    replace_in_file('src/podofo/private/XmlUtils.h', 'xmlErrorPtr error_', 'const xmlError *error_')
    replace_in_file('src/podofo/main/PdfXMPPacket.cpp', '#include <libxml/xmlsave.h>', '#include <libxml/xmlsave.h>\n#include <libxml/parser.h>')

    cmake_build(
        make_args='podofo_shared',
        PODOFO_BUILD_LIB_ONLY='TRUE',
        PODOFO_BUILD_STATIC='FALSE',
    )


def modify_excludes(excludes):
    excludes.discard('doc')
