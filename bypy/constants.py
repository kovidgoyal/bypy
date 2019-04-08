#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os


def base_dir():
    ans = getattr(base_dir, 'ans', None)
    if ans is None:
        ans = base_dir.ans = os.path.abspath('bypy')
    return ans
