# -*- coding: utf-8 -*-
"""Print every asset name in a small zone (dir-plausibility scan, all types)."""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
ASSET_BASE = 0x28
PTR_INLINE = 0xFFFFFFFF

d = open(ZONE, 'rb').read()
N = len(d)
print('zone bytes', N)


def plausible(o):
    if o + 16 > N:
        return False
    t, off, ptr, sz = struct.unpack_from('<4I', d, o)
    return (t < 64 and off < N and sz < N and off + sz <= N and ptr in (0, PTR_INLINE))


runs = []
o = 0
while o + 16 <= N:
    if plausible(o):
        s = o
        n = 0
        while o + 16 <= N and plausible(o):
            n += 1
            o += 16
        if n >= 2:
            runs.append((s, n))
    else:
        o += 1
runs.sort(key=lambda x: -x[1])
print('runs', [(hex(s), n) for s, n in runs[:8]])

for dir_off, count in runs[:2]:
    print('\n=== directory %#x count %d ===' % (dir_off, count))
    for i in range(count):
        typ, off, ptr, size = struct.unpack_from('<4I', d, dir_off + i * 16)
        blob = d[ASSET_BASE + off: ASSET_BASE + off + min(size, 300)]
        nm = ''
        if ptr == PTR_INLINE and len(blob) > 17:
            e = blob.find(b'\0', 16)
            if e > 16:
                nm = blob[16:e].decode('latin-1')
        print('  %4d type=%-3d off=%-8d size=%-7d %s' % (i, typ, off, size, nm))
