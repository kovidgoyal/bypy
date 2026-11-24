#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2026, Kovid Goyal <kovid at kovidgoyal.net>

# m4 is only needed at build time (by autoconf), as the m4 shipped with
# Xcode (GNU M4 1.4.6) is too old for modern autoconf.

allow_non_universal = True
