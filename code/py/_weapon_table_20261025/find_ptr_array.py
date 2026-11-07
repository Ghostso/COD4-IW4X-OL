# -*- coding: utf-8 -*-
"""Scan a CODOL runtime dump for a dense pointer array into weapon-name strings.

Builds the set of VAs at which a weapon-name-looking string starts, then finds
4-byte little-endian values that land on one of them. A run of >= 8 consecutive
such dwords is a candidate weapon-definition pointer table (bg_weaponDefs).
"""
import struct, sys, io, mmap, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

MEM = sys.argv[1]
IMAGE_BASE = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x400000
MIN_RUN = int(sys.argv[3]) if len(sys.argv) > 3 else 8

f = open(MEM, 'rb')
m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
N = len(m)
print('dump bytes', N, 'base', hex(IMAGE_BASE))

# candidate name string starts
name_va = set()
for mt in re.finditer(rb'(?<![\x20-\x7e])([a-z0-9_]{2,40}_mp)\x00', m):
    name_va.add(IMAGE_BASE + mt.start(1))
for mt in re.finditer(rb'(?<![\x20-\x7e])(defaultweapon_mp|none)\x00', m):
    name_va.add(IMAGE_BASE + mt.start(1))
print('candidate weapon-name strings:', len(name_va))

# scan dwords
hits = bytearray(N // 4 + 1)
for i in range(0, N - 4, 4):
    v = struct.unpack_from('<I', m, i)[0]
    if v in name_va:
        hits[i // 4] = 1

runs = []
i = 0
n = len(hits)
while i < n:
    if hits[i]:
        s = i
        while i < n and hits[i]:
            i += 1
        if i - s >= MIN_RUN:
            runs.append((s * 4, i - s))
    else:
        i += 1
print('runs >= %d:' % MIN_RUN, len(runs))
for off, cnt in sorted(runs, key=lambda x: -x[1])[:15]:
    print('  file %#x  va %#x  count %d' % (off, IMAGE_BASE + off, cnt))
