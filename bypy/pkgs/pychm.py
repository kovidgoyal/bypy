#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


import os
import shutil

from bypy.constants import PREFIX, iswindows
from bypy.utils import python_build, python_install, replace_in_file

if iswindows:
    def main(args):
        p = PREFIX.replace('\\', '/')
        shutil.copy(os.path.join(PREFIX, 'src', 'chm_lib.c'), 'chm')
        shutil.copy(os.path.join(PREFIX, 'src', 'lzx.c'), 'chm')
        shutil.copy(os.path.join(PREFIX, 'src', 'lzx.h'), 'chm')
        shutil.copy(os.path.join(PREFIX, 'include', 'chm_lib.h'), 'chm')
        replace_in_file(
            "chm/_chmlib.c",
            '"Search the CHM"},',
            '"Search the CHM"}, {NULL}'
        )
        replace_in_file(
            'setup.py',
            'search.c"',
            'search.c", "chm/chm_lib.c", "chm/lzx.c"'
        )
        replace_in_file(
            'setup.py',
            'libraries=["chm"]',
            f'include_dirs=["{p}/include"],'
            'define_macros=[("strcasecmp", "_stricmp"),'
            '("strncasecmp", "_strnicmp"), ("WIN32", "1")],'
        )
        python_build()
        python_install()
