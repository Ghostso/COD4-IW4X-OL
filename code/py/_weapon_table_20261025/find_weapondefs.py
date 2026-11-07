# -*- coding: utf-8 -*-
"""Find bg_weaponDefs in a client memory dump: an array of >=100 pointers whose
targets each begin with a pointer into the weapon-name string block."""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

MEM = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin'
IMAGE_BASE = 0x400000
NAME_LO, NAME_HI = 0xDB0000, 0xDE0000
MIN_RUN = 100

d = open(MEM, 'rb').read()
N = len(d)


def u32(va):
    off = va - IMAGE_BASE
    if off < 0 or off + 4 > N:
        return None
    return struct.unpack_from('<I', d, off)[0]


# 1. addresses (VAs) of dwords that point into the name block
name_ptr_sites = set()
for i in range(0, N - 4, 4):
    v = struct.unpack_from('<I', d, i)[0]
    if NAME_LO <= v < NAME_HI:
        name_ptr_sites.add(IMAGE_BASE + i)
print('name-pointer sites:', len(name_ptr_sites))

# 2. arrays of pointers whose target starts with a name pointer
hit = bytearray(N // 4 + 1)
for i in range(0, N - 4, 4):
    v = struct.unpack_from('<I', d, i)[0]
    if v in name_ptr_sites:
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
for off, cnt in sorted(runs, key=lambda x: -x[1])[:10]:
    print('  file %#x va %#x count %d' % (off, IMAGE_BASE + off, cnt))
    for k in range(min(cnt, 5)):
        st = struct.unpack_from('<I', d, off + 4 * k)[0]
        np = u32(st)
        s = ''
        if np is not None and NAME_LO <= np < NAME_HI:
            o = np - IMAGE_BASE
            e = d.find(b'\0', o, o + 64)
            s = d[o:e].decode('latin-1')
        print('     [%d] struct=%#x name=%#x %r' % (k, st, np or 0, s))
