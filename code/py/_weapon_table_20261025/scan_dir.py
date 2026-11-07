# -*- coding: utf-8 -*-
"""Generic 16-byte directory-run scan over an inflated CODOL zone."""
import struct, sys, io, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
d = open(ZONE, 'rb').read()
N = len(d)
print('zone bytes', N)


def ok(o):
    if o + 16 > N:
        return False
    t, off, ptr, sz = struct.unpack_from('<4I', d, o)
    return (t < 64 and off < N and sz < N and off + sz <= N and ptr in (0, 0xffffffff))


runs = []
o = 0
while o + 16 <= N:
    if ok(o):
        s = o
        rec = []
        while o + 16 <= N and ok(o):
            rec.append(struct.unpack_from('<4I', d, o))
            o += 16
        if len(rec) >= 20:
            runs.append((s, rec))
    else:
        o += 1
print('runs', len(runs))
for s, r in sorted(runs, key=lambda x: -len(x[1]))[:10]:
    print(hex(s), len(r), collections.Counter(x[0] for x in r),
          'first', r[:3], 'last', r[-3:])
