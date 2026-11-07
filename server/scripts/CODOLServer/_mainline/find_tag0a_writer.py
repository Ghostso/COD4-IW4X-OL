"""找 11/4 上行的真正序列化器。

实测 payload 开头:
    0a <u64 roomId> 13 08 <u32 len> <batch> 08 <u32>

要找的代码形态:
    push 0xa / mov byte [..],0xa   -> 写 tag 0x0a
    然后写一个 u64

而 0x13/0x08 那对已确认在位流写器里也出现(0xB77B10)，
但位流写器写的是 5 位常量，不是字节 0x13。
所以真正要搜的是**按字节写** 0x0a 的地方。

做法: 在整个 .text 里找 `6a 0a`(push 0xa) 且后续 3 条指令内
有写 8 字节(或 push 8 后跟两次 dword 写)的形态。
先粗略列出所有 push 0xa 的点，人工筛。
"""
import os
import struct

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

# 只在 EXE 主代码段搜(0x400000..0x1000000)
print('=== 搜 "push 0xa" 后紧接 8 字节写的候选 ===')
cands = []
for base, size, fn, prot in regions:
    if not (prot & 0x20):
        continue
    if not (0x400000 <= base < 0x1000000):
        continue
    data = blob(fn)
    if len(data) != size:
        continue
    i = data.find(b'\x6a\x0a')
    while i >= 0 and len(cands) < 300:
        seg = data[i:i + 32]
        # 后续 32 字节里出现 "push 8" 或对同一 buffer 写 dword
        if b'\x6a\x08' in seg or b'\x6a\x10' in seg:
            cands.append(base + i)
        i = data.find(b'\x6a\x0a', i + 1)

print('候选 %d 处（前 20）' % len(cands))
for va in cands[:20]:
    code = read_at(va - 0x8, 0x40)
    if not code:
        continue
    print()
    print('--- 0x%08X ---' % va)
    n = 0
    for ins in md.disasm(code, va - 0x8):
        mark = '  <<<' if ins.address == va else ''
        print('  %08X  %-18s %s %s%s' % (ins.address, ins.bytes.hex(),
                                          ins.mnemonic, ins.op_str, mark))
        n += 1
        if n > 14:
            break
