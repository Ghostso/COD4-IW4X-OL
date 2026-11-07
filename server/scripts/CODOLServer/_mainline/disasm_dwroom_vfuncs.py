"""反汇编 dwRoomMessageStartGame 的虚函数，看它们做什么。

vtable @ 0x00DC751C:
  [0] 0x00625BE0
  [1] 0x00625CE0
  [2] 0x00DF9364  ← 非代码，vtable 边界
所以只有前 2 个是真虚函数。

反汇编它们，看是否包含字段解析（字符串比较、数值读取等）。
"""
import os
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regions = {}
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions[int(p[0], 16)] = (int(p[1], 16), p[4], int(p[2], 16))

CACHE = {}


def blob(b):
    if b not in CACHE:
        CACHE[b] = open(os.path.join(D, regions[b][1]), 'rb').read()
    return CACHE[b]


def read_at(va, n):
    for base, (size, fn, prot) in regions.items():
        if base <= va < base + size and va + n <= base + size:
            return blob(base)[va - base:va - base + n]
    return None


def disasm(va, nbytes=200, label=''):
    code = read_at(va, nbytes)
    print()
    print('=== %s @ 0x%08X ===' % (label, va))
    if not code:
        print('  (不可读)')
        return
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    cnt = 0
    for ins in md.disasm(code, va):
        print('  %08X  %-22s %s %s'
              % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        cnt += 1
        if cnt >= 40:
            break


TARGETS = [
    ('StartGame.vf0', 0x00625BE0),
    ('StartGame.vf1', 0x00625CE0),
    ('Ready.vf0',     0x006287D0),
    ('Ready.vf1',     0x00629090),
    ('Base.vf0',      0x00626650),
]

for label, va in TARGETS:
    disasm(va, 180, label)
