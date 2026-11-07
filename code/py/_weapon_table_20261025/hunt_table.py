# -*- coding: utf-8 -*-
"""Find the runtime weapon-name table in a CODOL full-memory dump.

Strategy: locate weapon name strings, then find pointer arrays that point at
them. A dense run of 4-byte pointers to weapon names is the engine's
weapon-definition name table (bg_weaponDefs order = wire weapon index).
"""
import struct, sys, io, mmap, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

MEM = sys.argv[1] if len(sys.argv) > 1 else \
    r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin'
IMAGE_BASE = 0x400000

f = open(MEM, 'rb')
m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
N = len(m)
print('dump bytes', N)

PROBE = [b'm4a1tech_mp', b'ak47_mp', b'cheytac_mp', b'wa2000_mp', b'mp5k_mp']

name_vas = {}
for p in PROBE:
    offs = []
    i = 0
    while True:
        i = m.find(p, i)
        if i < 0:
            break
        offs.append(i)
        i += 1
    name_vas[p] = offs
    print(p.decode(), len(offs), [hex(o) for o in offs[:12]])

# candidate VAs for one well-known name
targets = {}
for p, offs in name_vas.items():
    targets[p] = [o + IMAGE_BASE for o in offs]

for p, vas in targets.items():
    for va in vas[:4]:
        pat = struct.pack('<I', va)
        hits = []
        i = 0
        while True:
            i = m.find(pat, i)
            if i < 0:
                break
            hits.append(i)
            i += 1
        print('%s va=%#x ptr_hits=%d %s' % (p.decode(), va, len(hits),
                                            [hex(h) for h in hits[:10]]))
