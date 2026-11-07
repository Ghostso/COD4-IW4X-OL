"""反汇编 StartGame / P2PInfo / Ready 的接收端(deserialize), 以及推送信封解码器。

只读 MEMDUMP, 输出到文件。
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
    ('StartGame.deserialize 0x625CE0', 0x00625CE0, 0x300),
    ('StartGame.serialize 0x625BE0', 0x00625BE0, 0x120),
    ('P2PInfo.serialize 0x627FC0', 0x00627FC0, 0x120),
    ('P2PInfo.deserialize 0x6280B0', 0x006280B0, 0x300),
    ('Ready.deserialize 0x629090', 0x00629090, 0x160),
    ('RoomInfo.deserialize 0x627EE0', 0x00627EE0, 0x200),
    ('MsgBase.deserialize 0x627CE0', 0x00627CE0, 0x160),
    ('RoomMsg_dispatch_634870', 0x00634870, 0x260),
    ('inst_push_decode_7E7C90', 0x007E7C90, 0x120),
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

p = os.path.join(OUT, 'room_recv_disasm.txt')
open(p, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(p, len(lines), 'lines')
