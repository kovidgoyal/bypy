#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

import os
from bypy.constants import PREFIX, iswindows
from bypy.utils import ModifiedEnv, python_build, python_install, replace_in_file


def main(args):
    env = {}
    p = PREFIX.replace(os.sep, '/')
    env = dict(
        UNRAR_INCLUDE='{}/include'.format(p),
        UNRAR_LIBDIRS='{0}/lib'.format(p),
    )
    if iswindows:
        replace_in_file('src/unrardll/wrapper.cpp', ' ssize_t written', ' Py_ssize_t written')
    with ModifiedEnv(**env):
        python_build()
    python_install()


def install_name_change_predicate(x):
    return x.endswith('unrar.so')


def install_name_change(old_name, is_dep):
    bn = os.path.basename(old_name)
    if bn.startswith('libunrar'):
        return os.path.join(PREFIX, 'lib', bn)
    return old_name
