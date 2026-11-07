# -*- coding: utf-8 -*-
"""Decode pointer runs into the client dump's weapon-name block and report which
runs look like a weapon-definition name table."""
import struct, sys, io, json, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

MEM = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin'
DEFS = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\fixtures\common_mp_weapondefs_20261023.json'
IMAGE_BASE = 0x400000
LO, HI = 0xDB0000, 0xDE0000

d = open(MEM, 'rb').read()
N = len(d)
known = set(w['name'] for w in json.load(open(DEFS, encoding='utf-8'))['weapons'])


def read_cstr(va):
    o = va - IMAGE_BASE
    if o < 0 or o >= N:
        return None
    e = d.find(b'\0', o, min(N, o + 96))
    if e < 0:
        return None
    try:
        return d[o:e].decode('latin-1')
    except Exception:
        return None


hit = bytearray(N // 4 + 1)
for i in range(0, N - 4, 4):
    v = struct.unpack_from('<I', d, i)[0]
    if LO <= v < HI:
        hit[i // 4] = 1

runs = []
i = 0
n = len(hit)
while i < n:
    if hit[i]:
        s = i
        while i < n and hit[i]:
            i += 1
        if i - s >= 20:
            runs.append((s * 4, i - s))
    else:
        i += 1

print('runs >= 20 :', len(runs))
scored = []
for off, cnt in runs:
    names = []
    for k in range(cnt):
        va = struct.unpack_from('<I', d, off + 4 * k)[0]
        names.append(read_cstr(va))
    good = sum(1 for s in names if s in known)
    scored.append((good, cnt, off, names))

for good, cnt, off, names in sorted(scored, reverse=True)[:8]:
    print('\nfile %#x  entries %d  known-weapon names %d' % (off, cnt, good))
    print('   ', names[:12])
