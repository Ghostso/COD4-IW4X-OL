"""反汇编 +0x278 闸门的三处游戏代码写入点及其上下文。"""
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


md = Cs(CS_ARCH_X86, CS_MODE_32)
SITES = [
    ('+0x278 = 1', 0x0062CCCD),
    ('+0x278 = 1', 0x0062FBBB),
    ('+0x278 = 0', 0x0062B41C),
]

lines = []
for label, va in SITES:
    start = va - 0x60
    code = read_at(start, 0x110)
    lines.append('')
    lines.append('=== %s  写入点 0x%08X ===' % (label, va))
    if not code:
        lines.append('  (unreadable)')
        continue
    for ins in md.disasm(code, start):
        mark = '  <<<' if ins.address == va else ''
        lines.append('  %08X  %-22s %s %s%s'
                     % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
        if ins.address > va + 0x50:
            break

print('\n'.join(lines))
open(os.path.join(sys.argv[1] if len(sys.argv) > 1 else '.',
                  'room_gate_context.txt'), 'w', encoding='utf-8').write(
    '\n'.join(lines) + '\n')
