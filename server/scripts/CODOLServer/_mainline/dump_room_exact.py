"""精确反汇编我们要推送的房间消息, 按函数边界(ret / 下一个函数)截断。

覆盖: RoomInfo(+内联 0x624510)、RoomStateUpdated、MemberDetails、Ready、
      StartCountingDown(0x628320 共用体)、Vote(0x628430)、P2PInfo。
只读转储。
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
    ('RoomInfo.serialize 0x627EA0', 0x00627EA0),
    ('RoomInfo.inner 0x624510', 0x00624510),
    ('RoomStateUpdated.ser 0x6285B0', 0x006285B0),
    ('MemberDetails.ser 0x6261C0', 0x006261C0),
    ('Ready.ser 0x6287D0', 0x006287D0),
    ('StartCountingDown.ser 0x628320', 0x00628320),
    ('Vote.ser 0x628430', 0x00628430),
    ('P2PInfo.ser 0x627FC0', 0x00627FC0),
    ('StartGame.ser 0x625BE0', 0x00625BE0),
    ('ChangeTeam.ser 0x6281D0', 0x006281D0),
    ('RoomStateUpdated.de 0x628610', 0x00628610),
    ('MemberDetails.de 0x6263C0', 0x006263C0),
]

md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = []
for label, va in TARGETS:
    code = read_at(va, 0x400)
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

p = os.path.join(OUT, 'room_push_exact.txt')
open(p, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(p, len(lines), 'lines')
