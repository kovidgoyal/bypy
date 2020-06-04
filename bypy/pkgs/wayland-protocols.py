#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re
from glob import glob

from ..constants import PREFIX, build_dir
from ..utils import replace_in_file, simple_build


def main(args):
    simple_build()
    pcdir = os.path.join(build_dir(), 'lib/pkgconfig')
    os.makedirs(pcdir)
    for x in glob(os.path.join(build_dir(), 'share/pkgconfig/*.pc')):
        replace_in_file(x, re.compile(r'^prefix=.+$', re.M),
                        'prefix=%s' % PREFIX)
        os.rename(x, x.replace('/share/', '/lib/'))
