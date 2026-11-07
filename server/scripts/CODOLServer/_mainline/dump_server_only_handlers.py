"""对服务端专属 type（客户端从未上行过的）逐个反汇编 handler。

从未出现的 type: 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0A 0x0C 0x0D 0x0E
                 0x0F 0x10 0x11 0x12 0x13 0x14 0x15 0x16 0x17
                 0x1A 0x1B 0x1C 0x1D 0x1E 0x1F 0x20 0x21 0x22 0x23
                 0x24 0x25 0x26 0x27 0x2B 0x2C 0x2D 0x2E

对每个 handler，输出:
  - 完整反汇编到 ret
  - 它有没有做 roomId 校验 (cmp [reg+0x20] / cmp [reg+0x24])
  - 它有没有写房间对象字段
这样能看出哪些是"服务端推给客户端"的。

输出到文件。
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


TABLE = 0x00636F3C
raw = read_at(TABLE, 0x2F * 4)
entries = [struct.unpack_from('<I', raw, i * 4)[0] for i in range(0x2F)]

SERVER_ONLY = [0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0C, 0x0D,
               0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
               0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F, 0x20, 0x21, 0x22, 0x23,
               0x24, 0x25, 0x26, 0x27, 0x2B, 0x2C, 0x2D, 0x2E]

md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = []
summary = []

for t in SERVER_ONLY:
    va = entries[t]
    code = read_at(va, 0x400)
    lines.append('')
    lines.append('=' * 70)
    lines.append('type 0x%02X  handler 0x%08X' % (t, va))
    lines.append('=' * 70)
    if not code:
        lines.append('  (unreadable)')
        continue
    insns = []
    for ins in md.disasm(code, va):
        insns.append(ins)
        if ins.mnemonic == 'ret':
            break
    txt = ['%08X  %-20s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str)
           for i in insns]
    lines.extend('  ' + x for x in txt)

    # 特征统计
    body = '\n'.join(txt)
    feats = []
    if '[eax + 0x20]' in body or '[eax + 0x24]' in body:
        feats.append('roomId校验')
    if 'readBits' in body:
        feats.append('位流')
    if 'ret ' in body:
        pass
    summary.append((t, va, len(insns), feats))

out = os.path.join(OUT, 'server_only_handlers.txt')
open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')

print('%-6s %-10s %s' % ('type', 'handler', 'insns 特征'))
for t, va, n, feats in summary:
    print('0x%02X   0x%08X  %3d   %s' % (t, va, n, ', '.join(feats) if feats else ''))
print()
print('完整反汇编 -> %s' % out)
