# -*- coding: utf-8 -*-
"""Dump the rawfile (type 36) and stringtable (type 37) asset names from a zone,
plus the file's magic/header, and note rawfile sizes."""
import sys, io, struct, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
ASSET_BASE = 0x28
d = open(ZONE, 'rb').read()
N = len(d)
print('zone bytes', N, 'head', d[:16].hex())


def collect(o):
    t, off, ptr, sz = struct.unpack_from('<4I', d, o)
    return t, off, ptr, sz, (t < 64 and off < N and sz < N and off + sz <= N
                             and ptr in (0, 0xFFFFFFFF))


best = (0, None)
o = 0
while o + 16 <= N:
    ok = collect(o)[4]
    if ok:
        s, n = o, 0
        while o + 16 <= N and collect(o)[4]:
            n += 1
            o += 16
        if n > best[0]:
            best = (n, s)
    else:
        o += 1

count, dir_off = best
print('directory %#x count %d' % (dir_off, count))
for i in range(count):
    t, off, ptr, sz = struct.unpack_from('<4I', d, dir_off + i * 16)
    if t not in (36, 37):
        continue
    blob = d[ASSET_BASE + off: ASSET_BASE + off + min(sz, 400)]
    nm = ''
    if ptr == 0xFFFFFFFF:
        e = blob.find(b'\0', 16)
        if e > 16:
            nm = blob[16:e].decode('latin-1')
    print('  %4d type=%-3d off=%-7d size=%-7d %r' % (i, t, off, sz, nm))
