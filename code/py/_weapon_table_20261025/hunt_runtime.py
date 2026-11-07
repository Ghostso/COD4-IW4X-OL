# -*- coding: utf-8 -*-
"""Find the runtime weapon-name pointer table in a CODOL runtime memory dump.

The dump is a flat VA image starting at IMAGE_BASE (default 0x400000), so
VA = IMAGE_BASE + file_offset.
"""
import struct, sys, io, mmap

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

MEM = sys.argv[1]
IMAGE_BASE = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x400000
PROBES = [b'm4a1tech_mp', b'ak47_mp', b'cheytac_mp', b'wa2000_mp', b'aa12_mp']

f = open(MEM, 'rb')
m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
print('dump bytes', len(m), 'IMAGE_BASE', hex(IMAGE_BASE))

for p in PROBES:
    offs = []
    i = 0
    while True:
        i = m.find(p, i)
        if i < 0:
            break
        offs.append(i)
        i += 1
    print(p.decode(), 'file hits', len(offs), [hex(o) for o in offs[:8]])
    for o in offs[:3]:
        va = IMAGE_BASE + o
        pat = struct.pack('<I', va)
        hits = []
        j = 0
        while True:
            j = m.find(pat, j)
            if j < 0:
                break
            hits.append(j)
            j += 1
        print('   va=%#x ptr hits=%d %s' % (va, len(hits), [hex(h) for h in hits[:8]]))
