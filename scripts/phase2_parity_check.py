#!/usr/bin/env python3
"""Phase 2.1 - Functional Parity Validation utility.

This script loads the legacy monolithic `atlasexplorer.py` and the new
modular `atlasexplorer` package, enumerates public classes/functions, and
attempts to map them to detect missing or changed public API surface.

Run this from the repository root.
"""
import inspect
import importlib
import importlib.util
import ast
import os
import sys
from pathlib import Path


def load_legacy_module(path: Path):
    spec = importlib.util.spec_from_file_location("legacy_atlasexplorer", str(path))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        return mod
    except ModuleNotFoundError as e:
        # Can't import runtime dependency in this environment; fall back to AST parsing
        print(f"Warning: failed to import legacy module ({e}). Falling back to source parsing (AST).")
        return parse_legacy_source(path)
    except Exception as e:
        # Other errors while executing the legacy module - fall back to AST parsing
        print(f"Warning: error importing legacy module ({e}). Falling back to source parsing (AST).")
        return parse_legacy_source(path)


def _ast_arg_list(node: ast.FunctionDef) -> str:
    args = node.args
    parts = []
    # positional args
    for a in args.args:
        parts.append(a.arg)
    # vararg
    if args.vararg:
        parts.append('*' + args.vararg.arg)
    # kwonly args
    for a in args.kwonlyargs:
        parts.append(a.arg)
    # kwargs
    if args.kwarg:
        parts.append('**' + args.kwarg.arg)
    return '(' + ', '.join(parts) + ')'


def parse_legacy_source(path: Path):
    """Parse the legacy source file with AST and return a symbol map.

    Returned structure mirrors get_public_symbols_module but uses simple dict
    placeholders for functions and classes so we don't execute the file.
    """
    src = path.read_text()
    tree = ast.parse(src)
    symbols = {}

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith('_'):
                continue
            symbols[node.name] = {'_ast_func': True, 'signature': _ast_arg_list(node)}
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith('_'):
                continue
            methods = set()
            for n in node.body:
                if isinstance(n, ast.FunctionDef) and not n.name.startswith('_'):
                    methods.add(n.name)
            symbols[node.name] = {'_ast_class': True, 'methods': sorted(methods)}

    return symbols


def get_public_symbols_module(mod):
    # If mod is an AST-parsed dict, return it directly
    if isinstance(mod, dict):
        return mod

    symbols = {}
    for name, obj in inspect.getmembers(mod):
        if name.startswith("_"):
            continue
        if inspect.isclass(obj) or inspect.isfunction(obj):
            symbols[name] = obj
    return symbols


def get_package_exports(pkg_name: str):
    pkg = importlib.import_module(pkg_name)
    exports = {}
    exported_names = getattr(pkg, "__all__", None)
    if exported_names is None:
        # fallback: list public attributes
        exported_names = [n for n in dir(pkg) if not n.startswith("_")]

    for name in exported_names:
        try:
            exports[name] = getattr(pkg, name)
        except Exception:
            exports[name] = None
    return exports


def compare_signatures(legacy_obj, new_obj):
    try:
        # AST-class (dict) vs real class
        if isinstance(legacy_obj, dict) and legacy_obj.get('_ast_class') and inspect.isclass(new_obj):
            legacy_methods = set(legacy_obj.get('methods', []))
            new_methods = {n for n, _ in inspect.getmembers(new_obj, predicate=inspect.isfunction) if not n.startswith('_')}
            missing = legacy_methods - new_methods
            extra = new_methods - legacy_methods
            return {'type': 'class', 'missing_methods': sorted(missing), 'extra_methods': sorted(extra)}

        if inspect.isclass(legacy_obj) and inspect.isclass(new_obj):
            # compare public method names
            legacy_methods = {n for n, _ in inspect.getmembers(legacy_obj, predicate=inspect.isfunction) if not n.startswith('_')}
            new_methods = {n for n, _ in inspect.getmembers(new_obj, predicate=inspect.isfunction) if not n.startswith('_')}
            missing = legacy_methods - new_methods
            extra = new_methods - legacy_methods
            return {'type': 'class', 'missing_methods': sorted(missing), 'extra_methods': sorted(extra)}

        # AST-function vs real function
        if isinstance(legacy_obj, dict) and legacy_obj.get('_ast_func') and inspect.isfunction(new_obj):
            return {'type': 'function', 'legacy_sig': legacy_obj.get('signature'), 'new_sig': str(inspect.signature(new_obj))}

        if inspect.isfunction(legacy_obj) and inspect.isfunction(new_obj):
            return {'type': 'function', 'legacy_sig': str(inspect.signature(legacy_obj)), 'new_sig': str(inspect.signature(new_obj))}

    except Exception as e:
        return {'error': str(e)}

    return {'note': 'unsupported types for signature comparison'}


def main():
    repo_root = Path(__file__).resolve().parents[1]
    legacy_path = repo_root / 'atlasexplorer' / 'atlasexplorer.py'

    if not legacy_path.exists():
        print(f"Legacy module not found at {legacy_path}")
        sys.exit(1)

    print("Loading legacy monolithic module...")
    legacy = load_legacy_module(legacy_path)

    print("Gathering public symbols from legacy module...")
    legacy_symbols = get_public_symbols_module(legacy)

    print("Importing modular package 'atlasexplorer'...")
    # ensure repo root is on sys.path so package imports resolve
    sys.path.insert(0, str(repo_root))
    modular_exports = get_package_exports('atlasexplorer')

    # Gather mapping
    matched = {}
    missing = {}
    extras = []

    for name, lobj in legacy_symbols.items():
        if name in modular_exports and modular_exports[name] is not None:
            comp = compare_signatures(lobj, modular_exports[name])
            matched[name] = comp
        else:
            # Try finding in well-known modular modules
            found = None
            fallback_modules = [
                'atlasexplorer.core.client',
                'atlasexplorer.core.experiment',
                'atlasexplorer.analysis.reports',
                'atlasexplorer.core.config',
                'atlasexplorer.core.constants',
                'atlasexplorer.security.encryption',
                'atlasexplorer.network.api_client',
            ]
            for m in fallback_modules:
                try:
                    mod = importlib.import_module(m)
                    if hasattr(mod, name):
                        found = getattr(mod, name)
                        break
                except Exception:
                    continue

            if found is not None:
                comp = compare_signatures(lobj, found)
                matched[name] = {'mapped_module': m, 'comparison': comp}
            else:
                missing[name] = lobj

    # Also list extras exported by modular package that don't exist in legacy
    for name in modular_exports.keys():
        if name.startswith('_'):
            continue
        if name not in legacy_symbols:
            extras.append(name)

    # Report
    print('\nFunctional Parity Report')
    print('========================')
    print(f'Legacy public symbols: {len(legacy_symbols)}')
    print(f'Matched symbols: {len(matched)}')
    print(f'Missing in modular package: {len(missing)}')
    print(f'Additional modular exports: {len(extras)}')

    if matched:
        print('\nMatched details (sample up to 20):')
        for i, (name, detail) in enumerate(matched.items()):
            if i >= 20:
                break
            print(f' - {name}: {detail}')

    if missing:
        print('\nMissing symbols (legacy -> NOT FOUND in modular):')
        for name in sorted(missing.keys()):
            print(' - ' + name)

    if extras:
        print('\nExtra modular exports (not in legacy):')
        for name in sorted(extras):
            print(' - ' + name)

    # Exit code reflects missing items
    if missing:
        print('\nParity check: PARTIAL (missing symbols present)')
        sys.exit(2)
    else:
        print('\nParity check: OK (all legacy symbols mapped)')
        sys.exit(0)


if __name__ == '__main__':
    main()
