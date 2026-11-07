"""反汇编房间消息分发表 0x634870 的各分支处理函数。

0x634870 按消息类型跳转（switch[0..46]，表已在 envelope_chain_disasm.txt 中解出）。
这些处理函数是客户端**消费**房间消息的地方：它们把消息字段写进房间状态,
房间 UI 的「换图/准备/投票」按钮就靠这些状态点亮。

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


# 来自 envelope_chain_disasm.txt 的 switch 表
SWITCH = {
    0: 0x636F02, 1: 0x636EBA, 2: 0x63495A, 3: 0x634AC2, 4: 0x634C3C,
    5: 0x634D35, 6: 0x634F13, 7: 0x635399, 8: 0x6354A9, 9: 0x63550B,
    10: 0x6356B8, 11: 0x636EBA, 12: 0x6355C2, 13: 0x6357BB, 14: 0x635814,
    15: 0x635968, 16: 0x6359FC, 17: 0x635E57, 18: 0x6361B6, 19: 0x635F2C,
    20: 0x636336, 21: 0x6365A3, 22: 0x6367C3, 23: 0x6367F5, 24: 0x635D8F,
    25: 0x636EBA, 26: 0x636291, 27: 0x636715, 28: 0x635AC3, 29: 0x635B47,
    30: 0x635C5B, 31: 0x635BE6, 32: 0x6368A7, 33: 0x63693E, 34: 0x6369FD,
    35: 0x636ABE, 36: 0x636B6D, 37: 0x634CB3, 38: 0x636C1D, 39: 0x636CD1,
    40: 0x636EBA, 41: 0x636EBA, 42: 0x636EBA, 43: 0x6352DC, 44: 0x634A28,
    45: 0x636D7F, 46: 0x636E0A,
}

md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = []
for typ in sorted(SWITCH):
    va = SWITCH[typ]
    code = read_at(va, 0x260)
    lines.append('')
    lines.append('=== type=0x%02X (%d)  handler 0x%08X ===' % (typ, typ, va))
    if not code:
        lines.append('  (unreadable)')
        continue
    for ins in md.disasm(code, va):
        lines.append('  %08X  %-22s %s %s'
                     % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if ins.mnemonic == 'ret':
            break

p = os.path.join(OUT, 'room_msg_handlers.txt')
open(p, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(p, len(lines), 'lines')
