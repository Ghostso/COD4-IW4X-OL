#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Try TAS stream cipher with FILETIME-derived keys.

Read-only. Tests:
  1. TASData.dat (240 B) and TclsQmFix.dat (784 B)
  2. The nine 8081 UDP payloads

Key candidates come from st_atime/st_mtime/st_ctime of executable/data files
under the game tree and %ProgramData%\\Tencent\\TAS.
"""

import glob
import json
import math
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'COD OL', 'scripts'))
import tas_crypt as T  # noqa: E402

FILETIME_EPOCH_DELTA = 116444736000000000


def ft_from_unix_ns(ns):
    v = ns // 100 + FILETIME_EPOCH_DELTA
    return struct.pack('<II', v & 0xFFFFFFFF, (v >> 32) & 0xFFFFFFFF)


def ent(b):
    if not b:
        return 0.0
    c = [0] * 256
    for x in b:
        c[x] += 1
    n = float(len(b))
    return -sum((k / n) * math.log(k / n, 2) for k in c if k)


def score_text(b):
    printable = sum(1 for c in b if 32 <= c < 127 or c in (9, 10, 13, 0))
    ascii_run = 0
    best = 0
    for c in b:
        if 32 <= c < 127:
            ascii_run += 1
            best = max(best, ascii_run)
        else:
            ascii_run = 0
    markers = sum(b.count(m) for m in (b'SEMV', b'config', b'client',
                                       b'name=', b'\n', b'//', b'{', b'}'))
    return printable / float(len(b)), best, markers


def collect_keys():
    paths = []
    roots = [os.path.join(ROOT, 'COD OL'),
             os.path.join(os.environ.get('ProgramData', r'C:\ProgramData'),
                          'Tencent', 'TAS')]
    exts = ('.exe', '.dll', '.dat', '.cfg', '.ini', '.iw4', '.zip')
    for r in roots:
        for dirpath, dirnames, filenames in os.walk(r):
            low = dirpath.lower()
            if '985' in low or 'ace' in low or 'tenprotect' in low:
                continue
            for fn in filenames:
                if fn.lower().endswith(exts):
                    paths.append(os.path.join(dirpath, fn))
    keys = {}
    for p in paths:
        try:
            st = os.stat(p)
        except OSError:
            continue
        for kind, ns in (('m', st.st_mtime_ns), ('c', st.st_ctime_ns),
                         ('a', st.st_atime_ns)):
            keys.setdefault(ft_from_unix_ns(ns), '%s:%s' % (kind, p))
    # explicit fallbacks
    keys.setdefault(T.DEFAULT_KEY, 'TAS default 46D14CF9/EF1DC888')
    for kw in (b'TASData', b'TAS\x00\x00\x00\x00\x00', b'tcls', b'qmfix'):
        keys.setdefault((kw * 8)[:8], 'ascii:%s' % kw)
    return keys


def is_candidate(out):
    return (out[:2] in (b'ur', b'su') or b'ur' in out[:4] or
            out[:4] == b'SEMV' or out[:4] == b'QOSC' or
            b'QOS' in out[:32] or b'TCLS' in out[:32] or
            b'config' in out[:64])


def main():
    keys = collect_keys()
    print('candidate keys:', len(keys))

    targets = [
        ('TASData', open(os.path.join(
            os.environ.get('ProgramData', r'C:\ProgramData'),
            'Tencent', 'TAS', 'TASData.dat'), 'rb').read()),
        ('TclsQmFix', open(os.path.join(
            ROOT, 'COD OL', 'components', 'tclsqmfix',
            'TclsQmFix.dat'), 'rb').read()),
    ]
    pkt_path = os.path.join(ROOT, 'run_codol_001', 'runs', 'SINGLE_V3',
                            'local_listeners.jsonl')
    for line in open(pkt_path, encoding='utf-8', errors='replace'):
        o = json.loads(line)
        if 'data_hex' in o:
            targets.append(('udp%d' % len(targets),
                            bytes.fromhex(o['data_hex'])))

    best = {name: [] for name, _ in targets}
    hits = []
    for key, src in keys.items():
        for flag in (0, 1):
            # cached per-key tables
            for name, data in targets:
                out = T.transform(key, flag, data)
                if is_candidate(out):
                    hits.append((name, flag, key.hex(), src,
                                 out[:48].hex(), repr(out[:48])))
                sc, run, mk = score_text(out)
                best[name].append((sc + run / 100.0 + mk * 0.02, flag,
                                   key.hex(), src, out[:64]))
    print('')
    print('=== marker hits ===')
    for h in hits[:200]:
        print(h)
    print('')
    for name, _ in targets:
        best[name].sort(key=lambda x: -x[0])
        print('=== top for %s ===' % name)
        for sc, flag, kh, src, out in best[name][:6]:
            print('  %.3f flag=%d key=%s src=%s' % (sc, flag, kh, src))
            print('     %r' % out)


if __name__ == '__main__':
    main()
