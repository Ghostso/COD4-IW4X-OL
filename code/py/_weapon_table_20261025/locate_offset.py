# -*- coding: utf-8 -*-
"""Given a file offset inside an inflated zone, find which XAsset contains it
and print the asset's type, size and (if inline) its name."""
import struct, sys, io, os, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
TARGETS = [int(x, 0) for x in sys.argv[2:]]
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
print('directory %#x count %d' % (dir_off, count))

entries = []
for i in range(count):
    t, off, ptr, sz = struct.unpack_from('<4I', d, dir_off + i * 16)
    entries.append((ASSET_BASE + off, ASSET_BASE + off + sz, i, t, off, sz, ptr))

for target in TARGETS:
    print('\n=== offset %#x ===' % target)
    found = False
    for start, end, i, t, off, sz, ptr in entries:
        if start <= target < end:
            found = True
            nm = ''
            if ptr == 0xFFFFFFFF:
                blob = d[start:start + min(sz, 400)]
                e = blob.find(b'\0', 16)
                if e > 16:
                    nm = blob[16:e].decode('latin-1')
            print('  asset #%d type=%d off=%#x size=%d name=%r delta=%#x'
                  % (i, t, off, sz, nm, target - start))
            s = max(0, target - 96)
            for k in range(s, min(N, target + 160), 16):
                row = d[k:k + 16]
                print('    %#08x %-47s %s' % (k, ' '.join('%02x' % b for b in row),
                                              ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)))
            break
    if not found:
        print('  not inside any asset')
