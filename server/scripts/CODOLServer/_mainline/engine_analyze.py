#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
engine_analyze.py -- offline analysis of an engine_dump.py capture.

Reads engine_best.bin plus the targeted windows written by engine_dump.py,
extracts printable strings, finds code references to those strings, and
disassembles a short window around every hit. The goal is to replace guesswork
with actual runtime-decrypted engine code references.

Usage:
    python engine_analyze.py --dir <dump_dir> [--out <report.md>]
"""

import argparse
import json
import os
import re
import struct
import sys

try:
    import capstone
except Exception:
    capstone = None

ENGINE_BASE = 0x00994000
EXTRA_BASES = {
    'sentinel_table.bin': 0x00CA8000,
    'runtime_strings.bin': 0x00CD0000,
    'dispatch_table.bin': 0x00E83A00,
    'global_state.bin': 0x00E83C00,
    'libcurl_data.bin': 0x00D33000,
    'image_tail.bin': 0x00E50000,
    'vm_code.bin': 0x116A0000,
}

KEYWORDS = (
    'config', 'cfg', 'lobby', 'blaze', 'demonware', 'dwlobby', 'dvar',
    'server', 'host', 'port', 'http', 'https', 'iips', 'tcp', 'udp',
    'socket', 'connect', 'auth', 'login', 'online', 'master', 'match',
    'game', 'steam', 'qq.com', 'tencent', 'nfs', 'qos', 'stun', 'title',
    'account', 'ticket', 'session', 'client', 'service', 'url', 'address',
    'iw4', 'gsc', 'hks', 'scaleform', 'zone', 'fastfile', 'party', 'clan',
    'profile', 'stats', 'challenge', 'playlist', 'dedicated', 'bind',
)

ASCII_RE = re.compile(rb'[\x20-\x7e]{4,}')
UTF16_RE = re.compile(rb'(?:[\x20-\x7e]\x00){4,}')
IP_RE = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')


def load_region(path, base):
    with open(path, 'rb') as fh:
        return base, fh.read()


def extract_strings(blob, base, max_strings=20000):
    rows = []
    seen = set()
    for m in ASCII_RE.finditer(blob):
        s = m.group().decode('ascii', 'replace')
        va = base + m.start()
        key = (va, s)
        if key not in seen:
            seen.add(key)
            rows.append((va, 'ascii', s))
    for m in UTF16_RE.finditer(blob):
        raw = m.group()
        s = raw.decode('utf-16-le', 'replace')
        va = base + m.start()
        key = (va, s)
        if key not in seen:
            seen.add(key)
            rows.append((va, 'utf16', s))
    rows.sort(key=lambda r: r[0])
    return rows[:max_strings]


def interesting(s):
    low = s.lower()
    return any(k in low for k in KEYWORDS) or bool(IP_RE.search(s))


def find_imm_refs(code, base, target):
    """Find common x86-32 absolute references to target VA."""
    needle = struct.pack('<I', target)
    hits = []
    i = 0
    end = len(code) - 4
    while i <= end:
        if code[i:i + 4] == needle:
            kind = 'imm32'
            if i >= 1 and code[i - 1] == 0x68:
                kind = 'push'
            elif i >= 2 and code[i - 2] == 0x8d:
                kind = 'lea'
            elif i >= 1 and code[i - 1] in tuple(range(0xb8, 0xc0)):
                kind = 'mov_reg'
            elif i >= 2 and code[i - 2] in (0xa1, 0xa3):
                kind = 'mov_mem'
            hits.append((base + i - (1 if kind in ('push', 'mov_reg') else 2 if kind in ('lea', 'mov_mem') else 0), kind))
        i += 1
    return hits


def disasm_window(code, base, off, before=24, after=64):
    if capstone is None:
        return ''
    start = max(0, off - before)
    end = min(len(code), off + after)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    lines = []
    for ins in md.disasm(code[start:end], base + start):
        lines.append('0x%08X  %-24s %s %s' % (ins.address, ins.bytes.hex(' '),
                                              ins.mnemonic, ins.op_str))
    return '\n'.join(lines)


def resolve_xrefs(engine_base, engine_code, string_rows, extra_blobs):
    refs = []
    for va, enc, s in string_rows:
        if not interesting(s):
            continue
        # References to strings inside the engine window are usually direct
        # absolute immediates. Search every loaded window for them.
        for blob_base, blob in [(engine_base, engine_code)] + list(extra_blobs.items()):
            hits = find_imm_refs(blob, blob_base, va)
            for at, kind in hits[:8]:
                refs.append({
                    'string_va': va,
                    'encoding': enc,
                    'string': s,
                    'ref_va': at,
                    'ref_kind': kind,
                    'section': 'engine_best' if blob is engine_code else 'extra',
                })
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    best_path = os.path.join(args.dir, 'engine_best.bin')
    if not os.path.isfile(best_path):
        print('no engine_best.bin in %s; nothing to analyze' % args.dir)
        return 0
    base, engine = load_region(best_path, ENGINE_BASE)
    extra = {}
    for name, b in EXTRA_BASES.items():
        p = os.path.join(args.dir, name)
        if os.path.isfile(p):
            extra[b] = load_region(p, b)[1]
    runtime_json = os.path.join(args.dir, 'runtime_target_range.json')
    if os.path.isfile(runtime_json) and os.path.isfile(os.path.join(args.dir, 'runtime_code.bin')):
        import json as _json
        meta = _json.load(open(runtime_json, encoding='utf-8'))
        extra[int(meta['base'])] = load_region(
            os.path.join(args.dir, 'runtime_code.bin'), int(meta['base']))[1]

    all_rows = []
    for blob_base, blob in [(base, engine)] + sorted(extra.items()):
        rows = extract_strings(blob, blob_base)
        for va, enc, s in rows:
            if interesting(s):
                all_rows.append((va, enc, s))

    refs = resolve_xrefs(base, engine, all_rows, extra)

    out = args.out or os.path.join(args.dir, 'engine_analysis.md')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('# CODOL runtime engine analysis\n\n')
        fh.write('Dump directory: `%s`\n\n' % args.dir)
        fh.write('## Interesting strings\n\n')
        for va, enc, s in all_rows[:300]:
            fh.write('- `0x%08X` %-5s `%s`\n' % (va, enc, s))
        fh.write('\n## Code references\n\n')
        for r in refs[:400]:
            fh.write('### `0x%08X` -> string `0x%08X` (%s)\n\n'
                     % (r['ref_va'], r['string_va'], r['ref_kind']))
            fh.write('```text\n')
            if r['section'] == 'engine_best':
                off = r['ref_va'] - base
                fh.write(disasm_window(engine, base, off) + '\n')
            else:
                for blob_base, blob in extra.items():
                    if blob_base <= r['ref_va'] < blob_base + len(blob):
                        o = r['ref_va'] - blob_base
                        if blob_base == 0x116A0000 or os.path.isfile(
                                os.path.join(args.dir, 'runtime_target_range.json')):
                            fh.write(disasm_window(blob, blob_base, o) + '\n')
                        else:
                            fh.write(blob[o:o + 32].hex(' ') + '\n')
                        break
            fh.write('```\n\n')
        fh.write('## Summary\n\n')
        fh.write('strings=%d references=%d\n' % (len(all_rows), len(refs)))
    print('wrote', out)
    print('strings=%d references=%d' % (len(all_rows), len(refs)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
