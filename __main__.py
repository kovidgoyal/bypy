#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys

if len(sys.argv) < 2:
    raise SystemExit('Must provide a sub-command')

args = list(sys.argv)
subcommand = args[1]
del args[1]

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


if subcommand == 'main':
    from bypy.main import main
    main(args)
elif subcommand == 'linux':
    from bypy.linux import main
    main(args)
