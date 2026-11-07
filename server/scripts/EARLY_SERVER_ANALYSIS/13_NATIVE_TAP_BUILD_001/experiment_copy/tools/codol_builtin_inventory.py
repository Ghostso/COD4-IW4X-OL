"""Compare Python registrations, IW4, and optional T5 resolver catalogs to C.

Run after preprocessing scr_vm_main.c with CODOL_SERVER, so inactive upstream
branches and commented registrations cannot produce false coverage. This is a
name/binding inventory, not a claim of semantic compatibility across engines.
The reference modules are imported only from the explicitly supplied directory.
"""
import argparse
import collections
import inspect
import json
from pathlib import Path
import re
import sys


def python_sources(fn, root):
    """Locate the registered callable and the reference's known EFFECT target.

    Do not invoke builtins or interpret their bodies as compatibility evidence.
    The EFFECT counter wrapper stores its target in the `_f` default parameter.
    """
    sources = []
    def add(target, role):
        code = getattr(target, '__code__', None)
        if code is None:
            return
        try:
            path = Path(code.co_filename).resolve().relative_to(root).as_posix()
        except ValueError:
            return
        sources.append({'role': role, 'file': path, 'line': code.co_firstlineno,
                        'callable': target.__qualname__})
    add(fn, 'registered_callable')
    if (getattr(fn, '__module__', None) == 'builtin_surface' and
            getattr(fn, '__qualname__', None) == 'register_surface.<locals>.eff.<locals>.wrapped'):
        target = inspect.signature(fn).parameters['_f'].default
        add(target, 'effect_target')
    return sources


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reference', type=Path, required=True)
    ap.add_argument('--preprocessed', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--t5-catalog', type=Path, help='Verified codol_t5_builtin_catalog.py output')
    args = ap.parse_args()
    root = args.reference.resolve()
    sys.path[:0] = [str(root / 'gsc'), str(root)]
    from gscbuiltins import BuiltinTable
    from host import CaptureHost
    import builtin_surface
    catalog = json.loads((root / 'vendor/builtins/iw4_builtins.json').read_text(encoding='utf-8'))
    table = BuiltinTable(host=CaptureHost(), log=lambda _: None)
    native = collections.defaultdict(dict)
    for kind, name, body, developer in re.findall(
            r'Scr_Add(Function|Method)\s*\(\s*"([^"]+)"\s*,\s*(\w+)\s*,\s*([01]|qfalse|qtrue)\s*\)',
            args.preprocessed.read_text(encoding='utf-8')):
        native[name.lower()][kind.lower()] = {'binding': body, 'developer_only': developer in ('1', 'qtrue')}
    entries = {}
    def entry(name):
        return entries.setdefault(name.lower(), {'name': name.lower(), 'sources': [], 'expected_kinds': []})
    for kind in ('functions', 'methods'):
        for record in catalog[kind]:
            e = entry(record['name'])
            if 'iw4_catalog' not in e['sources']:
                e['sources'].append('iw4_catalog')
            e['expected_kinds'].append(kind[:-1])
    for name, fn in table.fns.items():
        e = entry(name)
        e['sources'].append('python_registry')
        e['python_refusal'] = name in builtin_surface.REFUSALS
        e['python_sources'] = python_sources(fn, root)
    appendix = (root / 'docs/BASE.md').read_text(encoding='utf-8').split('## Appendix A', 1)[1].split('Note on the T5 remainder', 1)[0]
    for line in appendix.splitlines():
        if not line.startswith('- '):
            continue
        for name in re.findall(r'`([a-z0-9_]+)`', line):
            e = entry(name)
            e['sources'].append('treyarch_named' if '[B]' in line or '[C]' in line else 'reference_scope')
    t5 = None
    if args.t5_catalog:
        t5 = json.loads(args.t5_catalog.read_text(encoding='utf-8'))
        for record in t5['entries']:
            e = entry(record['name'])
            if 't5_server_resolver' not in e['sources']:
                e['sources'].append('t5_server_resolver')
            if record['selected_by_resolver'] and record['kind'] not in e['expected_kinds']:
                e['expected_kinds'].append(record['kind'])
            e.setdefault('t5_records', []).append(record)
    for e in entries.values():
        e['native'] = native.get(e['name'], {})
        e['status'] = ('binding_present_semantics_unverified' if e['native'] and
                       all(k in e['native'] for k in e['expected_kinds']) else 'missing_binding')
    result = {
        'scope': ('IW4 catalog, live Python registry, BASE Appendix A, and verified T5 server resolver tables'
                  if t5 else 'IW4 catalog, live Python registry, and BASE Appendix A; wider T5 enumeration still required'),
        'warning': 'A registered name is not proof of implemented behavior. Python effects/refusals are not native implementations.',
        'counts': dict(collections.Counter(e['status'] for e in entries.values())),
        'entries': sorted(entries.values(), key=lambda e: e['name']),
    }
    if t5:
        result['t5_executable_sha256'] = t5['executable_sha256']
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
