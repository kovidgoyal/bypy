#!/usr/bin/env python
# License: GPLv3 Copyright: 2023, Kovid Goyal <kovid at kovidgoyal.net>

import os
import shutil

from bypy.constants import PYTHON, build_dir
from bypy.utils import relpath_to_site_packages, run


def main(args):
    # These poor sods have drunk all the "modern" python packaging koolaid so
    # building from source for a pure python package is too complex requiring
    # half a dozen finicky and badly packaged dependencies,
    # instead of just stdlib + setuptools. Just copy the source code
    # ourselves while shaking our heads sadly at this idiocy.
    dest = os.path.join(build_dir(), relpath_to_site_packages(), 'dateutil')
    shutil.move('dateutil', dest)


def post_install_check():
    code = '''\
from dateutil.parser import parse;
parse('2019-10-12')
    '''
    run(PYTHON, '-c', code, library_path=True)
