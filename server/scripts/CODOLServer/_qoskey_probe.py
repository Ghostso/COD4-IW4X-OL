#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only probe for QOS key material (8081 channel).

Gathers:
  A) KEY_CONTEXT regions around QoS / ticket / iv_seed names
  B) 8081 packet byte analysis (keystream-reuse tests)
  C) TCLS shared-memory handoff evidence
"""

import glob
import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def p(*a):
    print(*a)


def sec(name):
    p('')
    p('=' * 70)
    p('== ' + name)
    p('=' * 70)


def key_context_regions():
    sec('A) KEY_CONTEXT regions')
    path = os.path.join(ROOT, 'CODOLServer', 'KEY_CONTEXT_20260925.txt')
    d = open(path, 'rb').read()
    for off in (1547, 1710, 8189, 9907, 10059, 10107, 10310, 11411,
                13933, 13977, 30863, 30911, 33735, 34198):
        p('--- off %d' % off)
        p(repr(d[max(0, off - 80):off + 260]))


def packet_analysis():
    sec('B) 8081 packet keystream-reuse / structure tests')
    path = os.path.join(ROOT, 'run_codol_001', 'runs', 'SINGLE_V3',
                        'local_listeners.jsonl')
    pk = []
    for line in open(path, encoding='utf-8', errors='replace'):
        o = json.loads(line)
        if 'data_hex' in o:
            pk.append((o.get('peer'), bytes.fromhex(o['data_hex'])))

    for i, (peer, b) in enumerate(pk):
        p('#%d peer=%s len=%d tail=%s' % (i, peer, len(b), b[-6:].hex()))

    small = [(i, b) for i, (peer, b) in enumerate(pk) if len(b) == 84]
    p('84B packets: %s' % [i for i, _ in small])

    # If the same keystream is reused at the same offset, ciphertext XOR is
    # plaintext XOR. Two plaintexts of the same QoS struct should XOR to a
    # low-entropy result (many zero bytes).
    p('')
    p('-- pairwise XOR of 84B packets (same-offset keystream reuse test)')
    for a in range(len(small)):
        for b_ in range(a + 1, len(small)):
            ia, ba = small[a]
            ib, bb = small[b_]
            n = min(len(ba), len(bb)) - 6
            x = bytes(u ^ v for u, v in zip(ba[:n], bb[:n]))
            zeros = x.count(0)
            pr = sum(1 for c in x if 32 <= c < 127) / float(len(x))
            p('  %d^%d len=%d zeros=%d printable=%.3f  %s'
              % (ia, ib, n, zeros, pr, x[:40].hex()))

    # Look for repeated 27-byte block in packet #7 (the 756B one)
    sec('B2) repeated-block search inside each packet')
    for i, (peer, b) in enumerate(pk):
        body = b[:-6]
        seen = {}
        best = None
        for L in (8, 16, 24, 27, 32):
            seen = {}
            for off in range(0, len(body) - L, 1):
                chunk = body[off:off + L]
                if chunk in seen:
                    if best is None or L > best[0]:
                        best = (L, seen[chunk], off, chunk)
                    break
                seen[chunk] = off
        if best:
            p('#%d len=%d  first repeat L=%d at %d and %d  block=%s'
              % (i, len(b), best[0], best[1], best[2], best[3].hex()))
        else:
            p('#%d len=%d  no repeat for L in 8/16/24/27/32' % (i, len(b)))


def shm_evidence():
    sec('C) TCLS shared-memory handoff evidence')
    for f in ('shm_full_trace.jsonl', 'shm_full.jsonl', 'crash_full.jsonl',
              'shm_ready.jsonl', 'shm_noready.jsonl', 'shm_zero.jsonl'):
        pth = os.path.join(ROOT, 'CODOLServer', 'logs', f)
        if not os.path.exists(pth):
            continue
        names = set()
        txt = open(pth, encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'"name": "(TCLS[^"]*)"', txt):
            names.add(m.group(1))
        for m in re.finditer(r'"mapping_created".*', txt):
            p('%s: %s' % (f, m.group(0)[:200]))
        if names:
            p('%s: mapping names = %s' % (f, sorted(names)[:5]))
        # region sizes seen
        for m in re.finditer(r'"region[^"]*":\s*\{[^}]*\}', txt):
            p('  region: %s' % m.group(0)[:200])


def tas_files():
    sec('D) TASData.dat / TclsQmFix.dat / TAS family files')
    cands = [
        os.path.join(os.environ.get('ProgramData', r'C:\ProgramData'),
                     'Tencent', 'TAS', 'TASData.dat'),
        os.path.join(ROOT, 'CODOLServer', 'tasdata_sample.bin'),
        os.path.join(ROOT, 'COD OL', 'components', 'tclsqmfix', 'TclsQmFix.dat'),
    ]
    for c in cands:
        if os.path.exists(c):
            d = open(c, 'rb').read()
            p('%s  len=%d  sha256=%s' % (c, len(d),
                                         __import__('hashlib').sha256(d).hexdigest()))
            p('   head: %s' % d[:64].hex())
        else:
            p('%s  MISSING' % c)

    # search whole TCLS tree for small .dat files
    p('')
    p('-- TCLS *.dat (size < 4096)')
    for f in glob.glob(os.path.join(ROOT, 'COD OL', 'TCLS', '**', '*.dat'),
                       recursive=True):
        try:
            n = os.path.getsize(f)
        except OSError:
            continue
        if n < 4096:
            p('   %7d  %s' % (n, os.path.relpath(f, ROOT)))


def name_sources():
    sec('E) which binaries contain the QoS/ticket key names')
    hits = os.path.join(ROOT, 'run_codol_001', 'runs', 'EARLY_HANDLE_SCAN',
                        'hits.jsonl')
    want = ['qos_cs', 'qos_ss', 'QOS_CS_MAGIC', 'QOS_SS_MAGIC', 'iv_seed',
            'lsg_server_ticket', 'server_ticket', 'client_ticket', 'cd_key',
            'TASData', 'TCLS_SHAREDMEMEMORY', '356c4bc3']
    for line in open(hits, encoding='utf-8', errors='replace'):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        t = o.get('text', '')
        for w in want:
            if w in t:
                p('%-18s va=0x%08X protect=%s' % (w, o.get('va', 0),
                                                  o.get('protect')))
                p('     %r' % t[:200])
                break


if __name__ == '__main__':
    key_context_regions()
    packet_analysis()
    shm_evidence()
    tas_files()
    name_sources()
