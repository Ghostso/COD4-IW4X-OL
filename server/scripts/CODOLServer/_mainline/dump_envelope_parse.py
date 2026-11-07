"""反汇编 0x7F1060 全函数, 看它传给 0x7E7C90 的两个 key 从哪来。

0x7F1060 是 dwLobbyEventHandler 槽6, 参数:
    [ebp+8]  [ebp+0xc]  [ebp+0x10]  [ebp+0x14]  [ebp+0x18]  [ebp+0x1c] [ebp+0x20] [ebp+0x24]
调用 0x7E7C90 时压栈顺序(从 0x7F1086 起):
    push [ebp+0x24] / push ebx=[ebp+0x20] / push edi(local)
    push [ebp+0xc] / push [ebp+0x10] / push [ebp+8] / push [ebp+0xc]? 需实测
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
    ('0x7F1060 slot6 (完整)', 0x007F1060, 0x120),
    ('0x7F3440 (被 slot6 先调)', 0x007F3440, 0x180),
    ('0x7F0A00 slot0', 0x007F0A00, 0x100),
    ('0x7F08B0', 0x007F08B0, 0x140),
]

md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = []
for label, va, n in TARGETS:
    code = read_at(va, n)
    lines.append('')
    lines.append('=== %s @ 0x%08X ===' % (label, va))
    if not code:
        lines.append('  (unreadable)')
        continue
    for ins in md.disasm(code, va):
        lines.append('  %08X  %-22s %s %s'
                     % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if ins.mnemonic == 'ret':
            break

txt = '\n'.join(lines)
out = os.path.join(sys.argv[1] if len(sys.argv) > 1 else '.', 'envelope_parse.txt')
open(out, 'w', encoding='utf-8').write(txt + '\n')
print(txt)
