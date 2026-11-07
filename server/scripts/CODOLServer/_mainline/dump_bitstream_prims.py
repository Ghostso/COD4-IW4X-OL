"""反汇编房间信道容器层的读者/写者, 以及 0x6371F0 的调用者。

目标: 确定 11/4 batch 里那 4 字节长度前缀之后的真实位流语义。
只读转储。
"""
import os
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
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


def read_at(va, n):
    for base, size, fn, _p in regions:
        if base <= va < base + size and va + n <= base + size:
            return blob(fn)[va - base:va - base + n]
    return None


def find_calls(target, limit=8):
    hits = []
    for base, size, fn, prot in regions:
        if not (prot & 0x20 or prot & 0x4 or prot & 0x2):
            continue
        data = blob(fn)
        if len(data) != size:
            continue
        for i in range(size - 5):
            if data[i] != 0xE8:
                continue
            rel = struct.unpack_from('<i', data, i + 1)[0]
            if base + i + 5 + rel == target:
                hits.append(base + i)
                if len(hits) >= limit:
                    return hits
    return hits


TARGETS = [
    ('bits_needed 0xB75D40', 0x00B75D40, 0x80),
    ('read_data 0xB772E0', 0x00B772E0, 0x90),
    ('buf_realloc 0xB77710', 0x00B77710, 0x80),
    ('grow 0xB77560', 0x00B77560, 0x60),
    ('reader_0xB76AF0', 0x00B76AF0, 0xB0),
    ('chan_outer_caller_probe', 0x006371F0, 0),
]

md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = []
for label, va, n in TARGETS:
    if n == 0:
        hits = find_calls(va)
        lines.append('')
        lines.append('=== callers of 0x%08X : %s ===' % (va, [hex(h) for h in hits]))
        for h in hits[:2]:
            code = read_at(h - 0x40, 0x90)
            if not code:
                continue
            lines.append('  --- context before 0x%08X ---' % h)
            for ins in md.disasm(code, h - 0x40):
                lines.append('  %08X  %-22s %s %s'
                             % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        continue
    code = read_at(va, n)
    lines.append('')
    lines.append('=== %s ===' % label)
    if not code:
        lines.append('  (unreadable)')
        continue
    for ins in md.disasm(code, va):
        lines.append('  %08X  %-22s %s %s'
                     % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if ins.mnemonic == 'ret':
            break

p = os.path.join(OUT, 'bitstream_prims.txt')
open(p, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(p, len(lines))
