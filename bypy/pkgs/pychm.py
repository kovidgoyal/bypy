#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


from bypy.constants import PREFIX, iswindows
from bypy.utils import python_build, python_install, replace_in_file

if iswindows:
    def main(args):
        p = PREFIX.replace('\\', '/')
        replace_in_file(
            'setup.py',
            'libraries=["chm"]',
            f'libraries=["chmlib"], include_dirs=["{p}/include"],'
            f'library_dirs=["{p}/lib"],'
            'define_macros=[("strcasecmp", "_stricmp"),'
            '("strncasecmp", "_strnicmp")],'
            'extra_link_args=["/NODEFAULTLIB:MSVCRT"]'
        )
        python_build()
        python_install()
