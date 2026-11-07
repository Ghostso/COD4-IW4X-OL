# -*- coding: utf-8 -*-
"""Extract the contiguous alphabetical weapon-name pool inside common_mp.zone."""
import re, sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\common_mp.zone'
OUT = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\zone_name_pool.txt'

d = open(ZONE, 'rb').read()
anchor = d.find(b'm9_mp\x00')
print('anchor m9_mp at', hex(anchor))

# walk backwards and forwards over NUL-terminated tokens while they look like names
START_RE = re.compile(rb'^[a-z0-9][a-z0-9_]{1,60}$')


def back_to_start(pos):
    cur = pos
    while True:
        prev = d.rfind(b'\0', 0, cur - 1)
        if prev < 0:
            return 0
        tok = d[prev + 1:cur - 1]
        if not START_RE.match(tok):
            return cur
        cur = prev + 1


def forward_to_end(pos):
    cur = pos
    while True:
        nul = d.find(b'\0', cur)
        if nul < 0:
            return len(d)
        nxt = nul + 1
        e = d.find(b'\0', nxt)
        if e < 0:
            return nxt
        tok = d[nxt:e]
        if not START_RE.match(tok):
            return nul
        cur = nxt


start = back_to_start(anchor)
end = forward_to_end(anchor)
print('pool span %#x..%#x (%d bytes)' % (start, end, end - start))
pool = d[start:end].split(b'\0')
pool = [p.decode('latin-1') for p in pool if p]
print('tokens', len(pool))

weap = [p for p in pool if p.endswith(('_mp', '_so', '_zm'))]
print('weapon-ish', len(weap))
open(OUT, 'w', encoding='utf-8').write('\n'.join(pool) + '\n')
print('wrote', OUT)

for probe in ('m4a1tech_mp', 'vector_mp', 'm9_mp', 'ak47_mp', 'cheytac_mp'):
    print('%-16s index-in-pool=%s' % (probe, pool.index(probe) if probe in pool else None))
print('first 30:', pool[:30])
