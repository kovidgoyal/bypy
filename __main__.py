#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys
import re

if len(sys.argv) < 2:
    raise SystemExit('Must provide a sub-command')

args = list(sys.argv)
subcommand = args[1]
del args[1]

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


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


if subcommand == 'main':
    from bypy.main import main
    main(args)
elif subcommand == 'linux':
    from bypy.linux import main
    main(args)
elif subcommand == 'macos':
    from bypy.macos import main
    main(args)
else:
    raise SystemExit(f'Unknown subcommand: {subcommand}')
