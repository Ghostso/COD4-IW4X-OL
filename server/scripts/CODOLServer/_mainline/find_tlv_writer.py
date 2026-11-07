"""找写 `13 08 <u32 len> <data>` 这个 TLV 模式的代码。

上行 payload 实测:
    0a <u64> | 13 08 <u32 len> <batch> | 08 <u32>
这是 protobuf-ish 的手写编码。对应的汇编通常是:
    push 0x13 ; call writeByte      (或 mov byte [..], 0x13)
    push 0x08 ; call writeByte
    push len  ; call writeU32
    ...       ; writeData

更稳的切入: 找**常量 0x13 与 0x08 相邻出现**的代码(两个 push imm8)。
    6a 13 6a 08  /  6a 13 ... 6a 08
在 .text 里搜，并限定后面紧跟写长度的形态。
"""
import os
import struct
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
hits = []
for base, size, fn, prot in regions:
    if not (prot & 0x20):
        continue
    data = blob(fn)
    if len(data) != size:
        continue
    i = data.find(b'\x6a\x13')
    while i >= 0 and len(hits) < 200:
        seg = data[i:i + 24]
        if b'\x6a\x08' in seg[:16]:
            hits.append(base + i)
        i = data.find(b'\x6a\x13', i + 1)

print('"push 0x13 ... push 0x08" 候选 %d 处' % len(hits))
for va in hits[:12]:
    code = read_at(va - 0x10, 0x60)
    if not code:
        continue
    print()
    print('--- 0x%08X ---' % va)
    for ins in md.disasm(code, va - 0x10):
        mark = '  <<<' if ins.address == va else ''
        print('  %08X  %-18s %s %s%s' % (ins.address, ins.bytes.hex(),
                                          ins.mnemonic, ins.op_str, mark))
        if ins.address > va + 0x40:
            break
