# -*- coding: utf-8 -*-
"""Dump every localize (type 27) and (type 44) asset from an inflated zone,
showing the raw string blob so we can see name lists like the one at 0x4278."""
import struct, sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
OUT = sys.argv[2]
WANT_TYPES = tuple(int(x) for x in sys.argv[3].split(',')) if len(sys.argv) > 3 else (27, 44)
ASSET_BASE = 0x28

d = open(ZONE, 'rb').read()
N = len(d)


def plausible(o):
    if o + 16 > N:
        return False
    t, off, ptr, sz = struct.unpack_from('<4I', d, o)
    return (t < 64 and off < N and sz < N and off + sz <= N and ptr in (0, 0xFFFFFFFF))


runs = []
o = 0
while o + 16 <= N:
    if plausible(o):
        s, n = o, 0
        while o + 16 <= N and plausible(o):
            n += 1
            o += 16
        if n >= 20:
            runs.append((s, n))
    else:
        o += 1
runs.sort(key=lambda x: -x[1])
dir_off, count = runs[0]

os.makedirs(OUT, exist_ok=True)
k = 0
for i in range(count):
    t, off, ptr, sz = struct.unpack_from('<4I', d, dir_off + i * 16)
    if t not in WANT_TYPES:
        continue
    start = ASSET_BASE + off
    blob = d[start:start + sz]
    nm = ''
    if ptr == 0xFFFFFFFF and len(blob) > 17:
        e = blob.find(b'\0', 16)
        if e > 16:
            nm = blob[16:e].decode('latin-1')
    path = os.path.join(OUT, '%05d_t%d_%s.bin' % (i, t, nm.replace('/', '_')[:60] or 'noname'))
    open(path, 'wb').write(blob)
    k += 1
print('wrote', k, 'assets to', OUT)
