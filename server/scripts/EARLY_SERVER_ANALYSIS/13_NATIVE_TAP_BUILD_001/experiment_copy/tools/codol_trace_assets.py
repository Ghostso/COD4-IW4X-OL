"""Generate C1 one-shot debugger scripts and summarize observed asset loads.

Run with 32-bit CDB, stop at the executable entry point, then read arm.cdb
with $<. No DLL injection or on-disk client changes. Raw debugger logs can
contain client diagnostics; keep them outside source control.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import struct

ASSET_NAMES = ('physpreset phys_collmap xanim xmodelsurfs xmodel material '
               'pixelshader vertexshader vertexdecl techset image sound sndcurve '
               'loaded_sound col_map_sp col_map_mp com_map game_map_sp game_map_mp '
               'map_ents fx_map gfx_map lightdef ui_map font menufile menu localize '
               'weapon snddriverglobals fx impactfx aitype mptype character '
               'xmodelalias rawfile stringtable leaderboarddef structureddatadef '
               'tracer vehicle addon_map_ents weaponattach').split()


def prepare(executable, output):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    data = executable.read_bytes()
    pe = struct.unpack_from('<I', data, 60)[0]
    optional = pe + 24
    if struct.unpack_from('<H', data, optional)[0] != 0x10b:
        raise ValueError('Expected the 32-bit C1 image')
    base = struct.unpack_from('<I', data, optional + 28)[0]
    table = optional + struct.unpack_from('<H', data, pe + 20)[0]
    sections = [struct.unpack_from('<IIII', data, table + i * 40 + 8)
                for i in range(struct.unpack_from('<H', data, pe + 6)[0])]

    def read(va, size):
        for _, rva, rawsize, raw in sections:
            offset = va - base - rva
            if 0 <= offset and offset + size <= rawsize:
                return data[raw + offset:raw + offset + size]
        raise ValueError(f'Unmapped address {va:x}')

    if base != 0x400000 or read(0x4c8ed0, 8) != bytes.fromhex('51a1606a7c018b00'):
        raise ValueError('Image does not match the measured C1 dispatcher')
    insns = {i.address: i for i in Cs(CS_ARCH_X86, CS_MODE_32).disasm(read(0x4c8ed0, 0x374), 0x4c8ed0)}
    routes = {}
    for kind in range(44):
        pc, equal = 0x4c8ed8, False
        for _ in range(256):
            insn = insns[pc]
            next_pc = pc + insn.size
            if insn.mnemonic == 'test' and insn.op_str == 'eax, eax':
                equal = kind == 0
            elif insn.mnemonic == 'cmp' and insn.op_str.startswith('eax, '):
                equal = kind == int(insn.op_str.split(', ')[1], 0)
            elif insn.mnemonic in ('je', 'jne'):
                if equal == (insn.mnemonic == 'je'):
                    next_pc = int(insn.op_str, 0)
            elif insn.mnemonic == 'call':
                routes[str(kind)] = {'callsite': pc, 'loader': int(insn.op_str, 0)}
                break
            elif insn.mnemonic == 'ret':
                routes[str(kind)] = {'callsite': None, 'loader': None}
                break
            pc = next_pc
        else:
            raise ValueError(f'Dispatch traversal did not terminate for type {kind}')
    output.mkdir(parents=True, exist_ok=True)
    for kind, route in routes.items():
        route['name'] = ASSET_NAMES[int(kind)]
    if ' ' in str(output.resolve()):
        raise ValueError('Use an output directory without spaces for CDB script paths')
    manifest = {'sha256': hashlib.sha256(data).hexdigest(), 'image_base': base,
                'dispatcher': 0x4c8ed0, 'caller_return': 0x4b5d24,
                'routes_static': routes}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    arm = [f'.logopen /t {output.resolve()}\\trace.log']
    seen = set()
    breakpoint_id = 0
    for route in routes.values():
        callsite = route['callsite']
        if callsite is None or callsite in seen:
            continue
        seen.add(callsite)
        pre = '.printf "ASSET_PRE,%x,%x,%x,%x\\n", @$tid, dwo(@esi), @esi+8, dwo(@esi+8)'
        call = '.printf "ASSET_ROUTE,%x,%x,%x,%x\\n", @$tid, dwo(@esi), @eip, @eip+5+dwo(@eip+1)'
        post = '.printf "ASSET_POST,%x,%x,%x,%x\\n", @$tid, dwo(@esi), @esi+8, dwo(@esi+8)'
        kinds = [int(k) for k, r in routes.items() if r['callsite'] == callsite]
        condition = ' | '.join(f'(dwo(@esi) == {k:x})' for k in kinds)
        for address, command in ((callsite, pre+'; '+call), (callsite+5, post)):
            escaped = command.replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))
            # Shared epilogues can also be reached by no-op asset types. Only
            # consume the one-shot return probe for this callsite's type(s).
            arm.append(f'bp{breakpoint_id} {address:08x} ".if ({condition}) {{ bc {breakpoint_id}; {escaped} }}; gc"')
            breakpoint_id += 1
    arm += ['.echo CODOL_ONE_SHOT_TRACE_ARMED', 'g']
    (output / 'arm.cdb').write_text('\n'.join(arm) + '\n')
    print(json.dumps({'routes': sum(bool(v['loader']) for v in routes.values()), 'output': str(output.resolve())}))


def summarize(manifest, logs, output):
    spec = json.loads(manifest.read_text())
    counts = collections.defaultdict(collections.Counter)
    pending = {}
    issues = []
    for log in logs:
        for event, thread, kind, slot, value in re.findall(
                r'ASSET_(PRE|POST|ROUTE),([0-9a-f]+),([0-9a-f]+),([0-9a-f]+),([0-9a-f]+)',
                log.read_text(errors='replace'), re.I):
            thread, kind, slot, value = [int(x, 16) for x in (thread, kind, slot, value)]
            event = event.upper()
            counts[kind][event.lower()] += 1
            if event == 'PRE':
                if thread in pending:
                    issues.append({'issue': 'unpaired_pre', 'type': pending[thread][0]})
                pending[thread] = (kind, slot)
            elif event == 'POST':
                if pending.pop(thread, None) != (kind, slot):
                    issues.append({'issue': 'unpaired_post', 'type': kind})
                if value not in (0, 0xffffffff, 0xfffffffe):
                    counts[kind]['resolved'] += 1
            elif event == 'ROUTE':
                expected = spec['routes_static'].get(str(kind), {})
                if (slot, value) != (expected.get('callsite'), expected.get('loader')):
                    issues.append({'issue': 'route_mismatch', 'type': kind, 'callsite': slot, 'loader': value})
    report = {'sha256': spec['sha256'], 'types': {
        kind: dict(route, **counts.get(int(kind), {})) for kind, route in spec['routes_static'].items()},
        'issues': issues, 'pending_at_end': list(pending.values())}
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'observed_types': len(counts), 'counts': dict(counts), 'issues': len(issues)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('executable', type=Path)
    prep.add_argument('output', type=Path)
    report = sub.add_parser('summarize')
    report.add_argument('manifest', type=Path)
    report.add_argument('output', type=Path)
    report.add_argument('logs', type=Path, nargs='+')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.executable, args.output)
    else:
        summarize(args.manifest, args.logs, args.output)

