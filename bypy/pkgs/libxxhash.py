#!/usr/bin/env python
# License: GPLv3 Copyright: 2023, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import worker_env, is_cross_half_of_lipo_build, current_build_arch
from bypy.utils import simple_build, build_dir, replace_in_file

needs_lipo = True

def main(args):
    cflags = f"{worker_env['CFLAGS']} -O3"
    ldflags = f"{worker_env['LDFLAGS']}"
    if is_cross_half_of_lipo_build():
        cflags += f' -arch {current_build_arch()}'
        ldflags += f' -arch {current_build_arch()}'
    replace_in_file('Makefile', '/usr/local', build_dir())
    replace_in_file('Makefile', '$(SONAME_FLAGS)', '$(SONAME_FLAGS) -shared')
    simple_build(configure_name=None, make_args=(f'CFLAGS={cflags}', f'LDFLAGS={ldflags}'))
