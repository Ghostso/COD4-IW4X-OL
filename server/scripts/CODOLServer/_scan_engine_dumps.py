#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only scan of the ENGINE_DUMP_* snapshots for QoS key material.

The engine dumps are the 5 MB gap window starting at ENGINE_BASE 0x00994000.
We search for:
  * plaintext markers  qos_cs / qos_ss / QOS_CS_MAGIC / tqosconnd / ur
  * 32-bit constants that could be QOS_CS_MAGIC / QOS_SS_MAGIC
  * neighbouring high-entropy tables (candidate RC4/stream key or S-box)
No process is touched.
"""

import glob
import hashlib
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMPS = os.path.join(ROOT, 'run_codol_001', 'runs')
ENGINE_BASE = 0x00994000

MARKERS = [b'QOS_CS_MAGIC', b'QOS_SS_MAGIC', b'qos_cs', b'qos_ss',
           b'tqosconnd', b'QosResFlag', b'ConndIPPortList', b'GameSvrNum',
           b'iv_seed', b'server_ticket', b'client_ticket', b'356c4bc3',
           b'TCLS_SHAREDMEMEMORY', b'tqos_']


def entropy(b):
    import math
    if not b:
        return 0.0
    c = [0] * 256
    for x in b:
        c[x] += 1
    n = float(len(b))
    return -sum((k / n) * math.log(k / n, 2) for k in c if k)


def scan(path):
    d = open(path, 'rb').read()
    print('== %s  len=%d  ent=%.3f' % (os.path.relpath(path, ROOT), len(d),
                                       entropy(d)))
    for m in MARKERS:
        offs = []
        start = 0
        while True:
            i = d.find(m, start)
            if i < 0:
                break
            offs.append(i)
            start = i + 1
            if len(offs) > 6:
                break
        if offs:
            print('   %-20s %d hit(s) at %s' % (
                m.decode('latin1'), len(offs),
                ', '.join('0x%X (va=0x%08X)' % (o, ENGINE_BASE + o)
                          for o in offs)))
            o = offs[0]
            print('        ctx %r' % d[max(0, o - 24):o + 72])
    return d


def main():
    pats = [os.path.join(DUMPS, 'ENGINE_DUMP_*', 'engine', 'engine_best.bin'),
            os.path.join(DUMPS, 'ENGINE_ATTACH_*', 'engine', 'engine_best.bin')]
    seen = set()
    files = []
    for pat in pats:
        for f in sorted(glob.glob(pat)):
            h = hashlib.sha256(open(f, 'rb').read()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            files.append(f)
    print('unique engine_best dumps:', len(files))
    for f in files:
        scan(f)


if __name__ == '__main__':
    main()
