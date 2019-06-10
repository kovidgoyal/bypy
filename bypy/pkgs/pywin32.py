#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re

from bypy.constants import PREFIX, PYTHON, build_dir, is64bit
from bypy.utils import (ModifiedEnv, replace_in_file, rmtree, run,
                        windows_sdk_paths)


def main(args):
    replace_in_file('setup.py', 'self._want_assembly_kept = sys',
                    'self._want_assembly_kept = False and sys')
    # the exports in this file lead to linker errors with invalid export
    # specification
    replace_in_file('setup.py',
                    "export_symbol_file = 'com/win32com/src/PythonCOM.def',",
                    '')
    # get rid of some not needed modules and modules that dont build
    replace_in_file(
        'setup.py', 'def _why_cant_build_extension(self, ext):',
        '''def _why_cant_build_extension(self, ext):
        if ext.name in ('exchdapi', 'exchange', 'mapi', 'pythonservice',
                'win32ui', 'win32uiole', 'dde', 'Pythonwin'):
            return 'disabled by Kovid'
        ''')
    # dont copy the MFC Dlls since we have disabled the modules
    # that use them
    replace_in_file(
        'setup.py',
        re.compile(r'^\s+# The MFC DLLs.+?^\s+def ', re.DOTALL | re.MULTILINE),
        '    def ')
    # dont build scintilla (used by the disabled pythonwin)
    replace_in_file('setup.py', 'self._build_scintilla()', '')

    # CLSID_PropertyChangeArray is not useable
    replace_in_file('com/win32comext/propsys/src/propsys.cpp',
                    '#ifndef CLSID_PropertyChangeArray', '#if 0')
    replace_in_file('com/win32comext/propsys/src/propsys.cpp',
                    'PYCOM_INTERFACE_CLSID_ONLY (PropertyChangeArray),', '')
    # Undefined symbol
    replace_in_file(
        'win32/src/win32job.i',
        '#define JOB_OBJECT_RESERVED_LIMIT_VALID_FLAGS JOB_OBJECT_RESERVED_LIMIT_VALID_FLAGS',  # noqa
        '')
    # fix win32com trying to write to paths inside the installation folder
    replace_in_file(
        'com/win32com/__init__.py',
        "__gen_path__ = ''",
        'import tempfile; __gen_path__ = os.path.join(tempfile.gettempdir(), "gen_py", "%d.%d" % (sys.version_info[0], sys.version_info[1]))')  # noqa
    replace_in_file('com/win32com/client/gencache.py',
                    'except IOError:', 'except Exception:')
    p = windows_sdk_paths()
    with ModifiedEnv(MSSDK_INCLUDE=p['include'], MSSDK_LIB=p['lib']):
        run(PYTHON, 'setup.py', 'build',
            '--plat-name=' + ('win-amd64' if is64bit else 'win32'))
        run(PYTHON, 'setup.py', '-q', 'install', '--root', build_dir())
    base = os.path.relpath(PREFIX, '/')
    q = os.listdir(build_dir())[0]
    os.rename(os.path.join(build_dir(), base, 'private'),
              os.path.join(build_dir(), 'private'))
    rmtree(os.path.join(build_dir(), q))
    rmtree(os.path.join(build_dir(),
                        'private/python/Lib/site-packages/pythonwin'))


def modify_excludes(excludes):
    excludes.add('demos')
    excludes.add('Demos')
    excludes.add('HTML')
