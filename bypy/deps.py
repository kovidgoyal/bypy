#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import importlib
import os
import sys
from operator import itemgetter

from .constants import PKG, PREFIX, SOURCES, build_dir, ismacos, mkdtemp
from .download_sources import download, read_deps
from .utils import (create_package, ensure_clear_dir, extract_source_and_chdir,
                    fix_install_names, lcopy, python_build, python_install,
                    qt_build, rmtree, run_shell, set_title, simple_build)


def pkg_path(dep):
    return os.path.join(PKG, dep['name'])


def make_build_dir(dep_name):
    ans = None
    if ans is None:
        ans = mkdtemp(prefix=f'{dep_name}-')
    return ans


def build_dep(dep, args, dest_dir=PREFIX):
    dep_name = dep['name']
    set_title('Building ' + dep_name)
    owd = os.getcwd()
    output_dir = todir = make_build_dir(dep_name)
    build_dir(output_dir)
    idep = dep_name.replace('-', '_')
    try:
        m = importlib.import_module('bypy.pkgs.' + idep)
    except ImportError:
        module_dir = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'pkgs')
        if os.path.exists(os.path.join(module_dir, f'{idep}.py')):
            raise
        m = None
    tsdir = extract_source_and_chdir(os.path.join(SOURCES, dep['filename']))
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
    except (Exception, SystemExit):
        import traceback
        traceback.print_exc()
        print('\nDropping you into a shell')
        sys.stdout.flush(), sys.stderr.flush()
        run_shell()
        raise SystemExit(1)
    create_package(m, output_dir, pkg_path(dep))
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
    rmtree(todir)
    rmtree(tsdir)


def unbuilt(dep):
    return not os.path.exists(pkg_path(dep))


def install_package(pkg_path, dest_dir):
    for dirpath, dirnames, filenames in os.walk(pkg_path):
        for x in tuple(dirnames):
            d = os.path.join(dirpath, x)
            if os.path.islink(d):
                filenames.append(x)
                dirnames.remove(x)
                continue
            name = os.path.relpath(d, pkg_path)
            os.makedirs(os.path.join(dest_dir, name), exist_ok=True)
        for x in filenames:
            f = os.path.join(dirpath, x)
            name = os.path.relpath(f, pkg_path)
            lcopy(f, os.path.join(dest_dir, name))


def install_packages(which_deps, dest_dir=PREFIX):
    ensure_clear_dir(dest_dir)
    if not which_deps:
        return
    print(f'Installing {len(which_deps)} previously compiled packages:',
          end=' ')
    sys.stdout.flush()
    for dep in which_deps:
        pkg = pkg_path(dep)
        if os.path.exists(pkg):
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
    return lambda dep: dep['name'] in names


def main(parsed_args):
    accept_func = unbuilt
    all_deps = read_deps()
    all_dep_names = frozenset(map(itemgetter('name'), all_deps))
    if parsed_args.deps:
        accept_func = accept_func_from_names(parsed_args.deps)
        if frozenset(parsed_args.deps) - all_dep_names:
            raise SystemExit('Unknown dependencies: {}'.format(
                frozenset(parsed_args.deps) - all_dep_names))
    deps_to_build = tuple(filter(accept_func, all_deps))
    if not deps_to_build:
        raise SystemExit('No buildable deps were specified')
    names_of_deps_to_build = frozenset(map(itemgetter('name'), deps_to_build))
    other_deps = [
        dep for dep in all_deps if dep['name'] not in names_of_deps_to_build]
    init_env(other_deps)
    download(deps_to_build)

    built_names = set()
    for dep in deps_to_build:
        try:
            build_dep(dep, parsed_args)
            built_names.add(dep['name'])
            print(f'{dep["name"]} successfully built!')
        finally:
            remaining = tuple(
                    d['name'] for d in deps_to_build
                    if d['name'] not in built_names)
            if remaining:
                print('Remaining deps:', ', '.join(remaining))

    # After a successful build, remove the unneeded sw dir
    rmtree(PREFIX)
