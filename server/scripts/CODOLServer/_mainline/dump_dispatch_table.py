"""把 0x636f3c 的分发表完整读出来，并对每个 type 反汇编其 handler 的开头。

0x634870 入口:
    readData(8) -> type
    cmp eax, 0x2e ; ja default
    jmp [eax*4 + 0x636f3c]

早先 dump 的 switch 表(0..46)是这份。现在要做的是:
  1. 确认表项数与每个 handler
  2. 每个 handler 开头看它读 body 的方式(位流 or 字节)
  3. 找出哪些 type 在客户端上行里从未出现 -> 服务端专属
"""
import glob
import json
import os
import re
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
N = 0x2F          # cmp eax,0x2e ; ja default -> 0..0x2e
raw = read_at(TABLE, N * 4)
if not raw:
    raise SystemExit('分发表不可读')

md = Cs(CS_ARCH_X86, CS_MODE_32)
print('=== 分发表 0x%08X (%d 项) ===' % (TABLE, N))
entries = []
for i in range(N):
    v = struct.unpack_from('<I', raw, i * 4)[0]
    entries.append(v)
    note = ''
    if v == 0x00636EBA:
        note = '  <- default'
    print('  type 0x%02X -> 0x%08X%s' % (i, v, note))

# 对每个非 default handler, 看开头 12 条指令里有没有位流读
print()
print('=== 各 handler 的 body 读取方式 ===')
print('  (watch: call 0xB774E0=readBits, 0xB772E0=readData, 0x4f3eb0=memcpy)')
for i, v in enumerate(entries):
    if v == 0x00636EBA:
        continue
    code = read_at(v, 0x60)
    if not code:
        continue
    ops = []
    for n, ins in enumerate(md.disasm(code, v)):
        if n > 14:
            break
        o = ins.op_str
        if ins.mnemonic == 'call':
            t = int(o, 16) if o.startswith('0x') else None
            if t == 0xB774E0:
                ops.append('readBits')
            elif t == 0xB772E0:
                ops.append('readData')
            elif t == 0x4F3EB0:
                ops.append('memcpy')
            elif t == 0x4F73B0 or t == 0x4F7680:
                ops.append('map/hash')
    if ops:
        print('  type 0x%02X 0x%08X: %s' % (i, v, ', '.join(ops[:5])))
