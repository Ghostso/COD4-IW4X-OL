# -*- coding: utf-8 -*-
"""Find dense pointer arrays into a given VA range inside a client memory dump.

Used to locate the engine's weapon-name pointer table (bg_weaponDefs names)
in the live client image.
"""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

MEM = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin'
IMAGE_BASE = 0x400000
LO, HI = 0xDB0000, 0xDE0000   # observed weapon-name string block in this dump
MIN_RUN = 6

d = open(MEM, 'rb').read()
N = len(d)

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
        if i - s >= MIN_RUN:
            runs.append((s * 4, i - s))
    else:
        i += 1

print('runs >= %d : %d' % (MIN_RUN, len(runs)))
for off, cnt in sorted(runs, key=lambda x: -x[1])[:20]:
    vals = [struct.unpack_from('<I', d, off + 4 * k)[0] for k in range(min(cnt, 6))]
    print('  file %#x va %#x count %d  first %s'
          % (off, IMAGE_BASE + off, cnt, [hex(v) for v in vals]))
