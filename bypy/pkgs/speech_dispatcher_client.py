#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import os
import shutil

from bypy.utils import python_major_minor_version, build_dir


def main(args):
    cl = 'src/api/python/speechd/client.py'
    major, minor = python_major_minor_version()
    ddir = os.path.join(
        build_dir(), 'lib', f'python{major}.{minor}', 'site-packages',
        os.path.basename(os.path.dirname(cl)))
    os.makedirs(ddir)
    open(os.path.join(ddir, '__init__.py'), 'w').close()
    with open(os.path.join(ddir, 'paths.py'), 'w') as f:
        f.write('import shutil; SPD_SPAWN_CMD = shutil.which("speech-dispatcher") or "/usr/bin/speech-dispatcher"')
    shutil.copyfile(cl, os.path.join(ddir, os.path.basename(cl)))
