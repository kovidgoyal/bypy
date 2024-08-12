#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re
import sys

args = list(sys.argv)
remove = []
for i, arg in enumerate(tuple(args)):
    m = re.match('([A-Z_]+)=(.+)', arg)
    if m is not None:
        remove.append(i)
        os.environ[m.group(1)] = m.group(2)
for r in reversed(remove):
    del args[r]


try:
    import certifi
except ImportError:
    pass
else:
    os.environ['SSL_CERT_FILE'] = certifi.where()


attr = None
if sys.stdout.isatty():
    try:
        import termios
    except ImportError:
        pass
    else:
        attr = termios.tcgetattr(sys.stdout.fileno())

try:
    from bypy.main import global_main
    global_main(args)
finally:
    if attr is not None:
        termios.tcsetattr(sys.stdout.fileno(), termios.TCSANOW, attr)
