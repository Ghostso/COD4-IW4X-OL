"""反汇编 0x637EB0 / 0x637FA0 —— 多个 dwRoomMessage 类共用的虚函数。

若它们是"把消息发出去"的入口，就能从里面读出 11/4 的真实线格式。
"""
import os
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

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


def read_at(va, n):
    for base, size, fn, _p in regions:
        if base <= va < base + size and va + n <= base + size:
            return blob(fn)[va - base:va - base + n]
    return None


TARGETS = [
    ('shared vfunc 0x637EB0', 0x00637EB0, 0x180),
    ('shared vfunc 0x637FA0', 0x00637FA0, 0x180),
    ('dwRoomImp vfunc 0x6391E0', 0x006391E0, 0x180),
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
        lines.append('  %08X  %-22s %s %s'
                     % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if ins.mnemonic == 'ret':
            break

txt = '\n'.join(lines)
out = os.path.join(sys.argv[1] if len(sys.argv) > 1 else '.', 'shared_vfuncs.txt')
open(out, 'w', encoding='utf-8').write(txt + '\n')
print(txt)
