"""把房间推送链的关键函数完整反汇编, 输出到文件(不刷屏)。

产物: <out>/room_chain_full.txt
只读 MEMDUMP, 不改任何东西。
"""
import os
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


TARGETS = [
    ('Manifold.deserialize 0x6256C0', 0x006256C0, 0x400),
    ('Manifold.serialize 0x625520', 0x00625520, 0x260),
    ('chan_outer 0x6371F0', 0x006371F0, 0x200),
    ('chan_inner 0x637000', 0x00637000, 0x200),
    ('msg_dispatch 0x634870', 0x00634870, 0x300),
    ('RoomInfo.inner 0x624510', 0x00624510, 0x200),
    ('push_receiver 0x7F1060', 0x007F1060, 0x80),
    ('writer_init 0xB779A0', 0x00B779A0, 0xC0),
    ('write_bits 0xB77B10', 0x00B77B10, 0x60),
    ('write_data 0xB777C0', 0x00B777C0, 0x80),
    ('read_bits 0xB774E0', 0x00B774E0, 0x60),
    ('read_data 0xB772E0', 0x00B772E0, 0x80),
    ('writer_core 0xB77A70', 0x00B77A70, 0x100),
    ('read_core 0xB77A00', 0x00B77A00, 0x80),
]

md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = []
for label, va, n in TARGETS:
    code = read_at(va, n)
    lines.append('')
    lines.append('=== %s ===' % label)
    if not code:
        lines.append('  (unreadable)')
        continue
    for ins in md.disasm(code, va):
        lines.append('  %08X  %-24s %s %s'
                     % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

p = os.path.join(OUT, 'room_chain_full.txt')
open(p, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(p, len(lines), 'lines')
