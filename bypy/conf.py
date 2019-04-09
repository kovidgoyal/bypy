#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import ast


def parse_conf_file(path_or_data_or_file_object):
    ans = {}
    if hasattr(path_or_data_or_file_object, 'read'):
        path_or_data_or_file_object = path_or_data_or_file_object.read()
    if isinstance(path_or_data_or_file_object, str):
        with open(path_or_data_or_file_object, 'rb') as f:
            path_or_data_or_file_object = f.read()
    for line in path_or_data_or_file_object.decode('utf-8').splitlines():
        line = line.strip()
        if line.startswith('#') or not line:
            continue
        key, rest = line.split(maxsplit=1)
        ans[key] = ast.literal_eval(rest.strip())
    return ans
