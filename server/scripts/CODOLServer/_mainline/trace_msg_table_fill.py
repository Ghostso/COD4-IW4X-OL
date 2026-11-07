"""追查 0x634870 入口 [ebx+0x1c] 的语义, 以及 0x82E1458 表的填充点。

已知:
    0063488A  cmp dword ptr [ebx+0x1c], 0
    006348A5  je  0x634907        ; 为 0 则跳过"读 type + 查表 + 调处理器"
    006348D8  mov esi,[eax*4+0x82E1458]
    006348E7  je  0x63494a        ; 表项为 0 -> 丢弃

问题: [ebx+0x1c] 是什么? 谁写 0x82E1458?

做法:
  1. 找所有 `mov ...,[reg+0x1c]` 与 0x634870 相关的调用点(哪个对象当 ebx)
  2. 全镜像搜写 0x82E1458 的指令 (mov [0x82E1458+..], reg / disp32)
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


TABLE = 0x082E1458
pat_le = struct.pack('<I', TABLE)
pat_be = struct.pack('>I', TABLE)

print('=== 搜 0x82E1458 的绝对地址引用(操作数里出现该立即数) ===')
hits = []
for base, size, fn, prot in regions:
    if not (prot & 0x20 or prot & 0x4 or prot & 0x2):
        continue
    data = blob(fn)
    if len(data) != size:
        continue
    i = data.find(pat_le)
    while i >= 0 and len(hits) < 40:
        hits.append(base + i)
        i = data.find(pat_le, i + 1)
print('  小端出现 %d 次:' % len(hits))
for h in hits[:20]:
    print('    0x%08X' % h)

print()
print('=== 反汇编包含这些引用的函数头(看是否是表初始化循环) ===')
md = Cs(CS_ARCH_X86, CS_MODE_32)
for h in hits[:6]:
    start = h - 0x40
    code = read_at(start, 0xC0)
    if not code:
        continue
    print('  --- around 0x%08X ---' % h)
    for n, ins in enumerate(md.disasm(code, start)):
        mark = '  <<<' if ins.address <= h < ins.address + ins.size else ''
        print('    %08X  %-20s %s %s%s' % (ins.address, ins.bytes.hex(),
                                           ins.mnemonic, ins.op_str, mark))
        if n > 22:
            break
