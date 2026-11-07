"""在内存转储里找房间对象 +0x278 / +0x283 两个字节闸门的写入点。

0x0F(RoomInfo) 处理器开头:
    cmp byte ptr [ebx+0x278], 0 ; jne 丢弃
    cmp byte ptr [ebx+0x283], 0 ; jne 丢弃
这两个字节决定客户端收不收房间信息。找谁写它们。

做法: 全镜像搜 `c6 83 78 02 00 00 <imm>` (mov byte ptr [ebx+0x278], imm)
      和 `c6 83 83 02 00 00 <imm>`, 以及 +0x278 的其他寻址形式。
"""
import os
import struct
import sys

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'

regions = []
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions.append((int(p[0], 16), int(p[1], 16), p[4], int(p[2], 16)))
CACHE = {}


def blob(fn):
    if fn not in CACHE:
        CACHE[fn] = open(os.path.join(D, fn), 'rb').read()
    return CACHE[fn]


PATTERNS = {
    'mov [ebx+0x278], imm8': b'\xc6\x83\x78\x02\x00\x00',
    'mov [ebx+0x283], imm8': b'\xc6\x83\x83\x02\x00\x00',
    'mov [ecx+0x278], imm8': b'\xc6\x81\x78\x02\x00\x00',
    'mov [ecx+0x283], imm8': b'\xc6\x81\x83\x02\x00\x00',
    'mov [eax+0x278], imm8': b'\xc6\x80\x78\x02\x00\x00',
    'mov [eax+0x283], imm8': b'\xc6\x80\x83\x02\x00\x00',
    'mov [esi+0x278], imm8': b'\xc6\x86\x78\x02\x00\x00',
    'mov [edi+0x278], imm8': b'\xc6\x87\x78\x02\x00\x00',
}

for name, pat in PATTERNS.items():
    hits = []
    for base, size, fn, prot in regions:
        if not (prot & 0x20 or prot & 0x4 or prot & 0x2):
            continue
        data = blob(fn)
        if len(data) != size:
            continue
        i = data.find(pat)
        while i >= 0 and len(hits) < 20:
            va = base + i
            val = data[i + len(pat)] if i + len(pat) < len(data) else None
            hits.append((va, val))
            i = data.find(pat, i + 1)
    if hits:
        print('%s:' % name)
        for va, val in hits:
            print('   0x%08X  imm=%s' % (va, ('0x%02X' % val) if val is not None else '?'))
    else:
        print('%s: 无命中' % name)
