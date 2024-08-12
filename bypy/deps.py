#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import importlib
import os
import sys
from operator import itemgetter

from .constants import (
    PKG, PREFIX, SOURCES, UNIVERSAL_ARCHES, build_dir, current_build_arch,
    currently_building_dep, ismacos, lipo_data, mkdtemp
)
from .download_sources import download, read_deps
from .utils import (
    RunFailure, create_package, ensure_clear_dir, extract_source_and_chdir,
    fix_install_names, install_package, lipo, python_build, python_install,
    qt_build, rmtree, run_shell, set_title, simple_build
)


def pkg_path(dep):
    return os.path.join(PKG, dep['name'])


def make_build_dir(dep_name):
    return mkdtemp(prefix=f'{dep_name}-')


def module_for_dep(dep):
    dep_name = dep['name']
    idep = dep_name.replace('-', '_')
    try:
        m = importlib.import_module('bypy.pkgs.' + idep)
    except ImportError:
        module_dir = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'pkgs')
        if os.path.exists(os.path.join(module_dir, f'{idep}.py')):
            raise
        m = None
    return m


class CleanupDirs:

    def __init__(self):
        self.dirs = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        for x in self.dirs:
            try:
                rmtree(x)
            except PermissionError:
                pass

    def __call__(self, x):
        self.dirs.append(x)


def build_once(dep, m, args, cleanup, target=None):
    base = dep['name']
    if target:
        base += f'.{target}.'
    output_dir = make_build_dir(base)
    build_dir(output_dir, target)
    cleanup(output_dir)
    cleanup(extract_source_and_chdir(os.path.join(SOURCES, dep['filename'])))
    try:
        if hasattr(m, 'main'):
            m.main(args)
        else:
            if 'python' in dep:
                python_build()
                python_install()
            elif dep['name'].startswith('qt-'):
                qt_build()
            else:
                simple_build()
        if ismacos:
            fix_install_names(m, output_dir)
    except RunFailure as e:
        print('\nRunning the following command failed:', file=sys.stderr)
        print(e.cmd)
        print('Dropping you into a shell', file=sys.stderr)
        sys.stdout.flush(), sys.stderr.flush()
        run_shell(env=e.env, cwd=e.cwd)
        raise SystemExit(1)
    except (Exception, SystemExit):
        import traceback
        traceback.print_exc()
        print('\nDropping you into a shell')
        sys.stdout.flush(), sys.stderr.flush()
        run_shell(cwd=build_dir())
        raise SystemExit(1)
    return output_dir


def build_dep(dep, args, dest_dir=PREFIX):
    current_build_arch(None)
    currently_building_dep(dep)
    dep_name = dep['name']
    owd = os.getcwd()
    m = module_for_dep(dep)
    needs_lipo = ismacos and getattr(
        m, 'needs_lipo', False) and len(UNIVERSAL_ARCHES) > 1
    with CleanupDirs() as cleanup:
        if needs_lipo:
            output_dirs = []
            lipo_data.clear()
            for arch in UNIVERSAL_ARCHES:
                output_dirs.append((arch, build_once(
                    dep, m, args, cleanup, target=arch)))
            build_dir(make_build_dir(dep_name))
            getattr(m, 'lipo', lipo)(output_dirs)
        else:
            build_once(dep, m, args, cleanup)

        if m is None and dep_name.startswith('qt-'):
            m = importlib.import_module('bypy.pkgs.qt_base')
        create_package(m, pkg_path(dep))
        install_package(pkg_path(dep), dest_dir)
        if hasattr(m, 'post_install_check'):
            try:
                m.post_install_check()
            except (Exception, SystemExit):
                import traceback
                traceback.print_exc()
                print('\nDropping you into a shell')
                sys.stdout.flush(), sys.stderr.flush()
                run_shell()
                raise SystemExit(1)
    os.chdir(owd)


def unbuilt(dep):
    return not os.path.exists(pkg_path(dep))


def install_packages(which_deps, dest_dir=PREFIX):
    ensure_clear_dir(dest_dir)
    paths = {dep['name']: pkg_path(dep) for dep in which_deps
             if os.path.exists(pkg_path(dep))}
    if not paths:
        return
    print(f'Installing {len(paths)} previously compiled packages:',
          end=' ')
    sys.stdout.flush()
    for dep in which_deps:
        if dep['name'] not in paths:
            continue
        pkg = paths[dep['name']]
        print(dep['name'], end=', ')
        sys.stdout.flush()
        install_package(pkg, dest_dir)
    print()
    sys.stdout.flush()


def init_env(which_deps=None):
    if which_deps is None:
        which_deps = read_deps()
    install_packages(which_deps)


def accept_func_from_names(names):
    names = frozenset(names)
    wants_qt = 'qt' in names

    def ffunc(dep):
        return dep['name'] in names or (
                wants_qt and dep['name'].startswith('qt-'))
    return ffunc


def main(parsed_args):
    accept_func = unbuilt
    all_deps = read_deps()
    all_dep_names = frozenset(map(itemgetter('name'), all_deps))
    if parsed_args.dependencies:
        accept_func = accept_func_from_names(parsed_args.dependencies)
        if (frozenset(parsed_args.dependencies) - {'qt'}) - all_dep_names:
            raise SystemExit('Unknown dependencies: {}'.format(
                frozenset(parsed_args.dependencies) - all_dep_names))
    deps_to_build = tuple(filter(accept_func, all_deps))
    if not deps_to_build:
        if accept_func is unbuilt:
            print('No unbuilt dependencies left')
            raise SystemExit(0)
        raise SystemExit('No buildable deps were specified')
    names_of_deps_to_build = frozenset(map(itemgetter('name'), deps_to_build))
    other_deps = [
        dep for dep in all_deps if dep['name'] not in names_of_deps_to_build]
    init_env(other_deps)
    download(deps_to_build)

    built_names = set()
    for i, dep in enumerate(deps_to_build):
        set_title(f'Building {dep["name"]} -- {i+1} of {len(deps_to_build)}')
        try:
            build_dep(dep, parsed_args)
            built_names.add(dep['name'])
            print(f'\x1b[36m{dep["name"]} successfully built!\x1b[m')
        finally:
            remaining = tuple(
                    d['name'] for d in deps_to_build
                    if d['name'] not in built_names)
            if remaining:
                print('Remaining deps:', ', '.join(remaining))

    # After a successful build, remove the unneeded sw dir
    rmtree(PREFIX)
