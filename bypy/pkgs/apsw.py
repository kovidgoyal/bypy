#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import PREFIX, PYTHON, build_dir, iswindows
from bypy.utils import python_build, python_install, run


def main(args):
    if iswindows:
        run(
            PYTHON, 'setup.py', 'fetch', '--all',
            '--missing-checksum-ok', 'build',
            '--enable-all-extensions', '--enable=load_extension',
            'install', '--root', build_dir()
        )
    else:
        python_build(extra_args=('--enable=load_extension'))
    python_install()


def install_name_change_predicate(x):
    return x.endswith('apsw.so')


def install_name_change(old_name, is_dep):
    bn = os.path.basename(old_name)
    if bn.startswith('libsqlite'):
        return os.path.join(PREFIX, 'lib', bn)
    return old_name


def post_install_check():
    code = '''import apsw; print(apsw); \
    c = apsw.Connection(":memory:"); \
    c.cursor().execute( \
    'CREATE VIRTUAL TABLE email USING fts5(title, body);')'''
    run(PYTHON, '-c', code, library_path=True)
