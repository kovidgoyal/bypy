#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import importlib
import os
import re
import sys

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


if subcommand == 'vm':
    if len(args) < 2:
        raise SystemExit(
            'You must provide a sub-command such as: run, shutdown, status')
    try:
        main = importlib.import_module(f'virtual_machine.{args[1]}').main
    except (ModuleNotFoundError, AttributeError):
        raise SystemExit(
            f'Unknown virtual machine sub-command: {args[1]},'
            ' common choices are: run, shutdown and status')
    del args[1]
    sys.argv = args
    main()
    sys.exit(0)
else:
    try:
        main = importlib.import_module(f'bypy.{subcommand}').main
    except (ImportError, AttributeError):
        raise SystemExit(f'Unknown sub-command: {subcommand}')
    main(args)
    sys.exit(0)
