"""定位 SetReadyState / GetReadyState 的实现。

这些是 Scaleform 的 ExternalInterface 方法名，C++ 侧有对应的
GFxFunctionHandler 或字符串比较分发。

搜法: 字符串地址在代码里的引用(xref) → 找到分发函数 → 反汇编。
"""
import os
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

NAMES = ['SetReadyState', 'GetReadyState', 'IsRoomHost', 'GetRoomInfo',
         'ChangeTeam', 'IsInRoom']

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


# 1) 找字符串地址
addr = {}
for base, size, fn, prot in regions:
    if not (0x00C00000 <= base < 0x01000000):
        continue
    d = blob(fn)
    if len(d) != size:
        continue
    for nm in NAMES:
        i = d.find(nm.encode() + b'\x00')
        while i >= 0:
            if i == 0 or d[i - 1] == 0:      # 串首
                addr.setdefault(nm, base + i)
            i = d.find(nm.encode() + b'\x00', i + 1)

print('=== 字符串地址 ===')
for nm in NAMES:
    print('  %-16s 0x%08X' % (nm, addr.get(nm, 0)))

md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = []
print()
print('=== 引用点 ===')
for nm in NAMES:
    a = addr.get(nm)
    if not a:
        continue
    needle = struct.pack('<I', a)
    hits = []
    for base, size, fn, prot in regions:
        if not (prot & 0x20):
            continue
        d = blob(fn)
        if len(d) != size:
            continue
        i = d.find(needle)
        while i >= 0 and len(hits) < 10:
            if (base + i) % 4 == 0:
                hits.append(base + i)
            i = d.find(needle, i + 1)
    print('  %-16s 被引用 %d 处: %s' % (nm, len(hits), [hex(h) for h in hits[:5]]))
    lines.append('')
    lines.append('=== %s 0x%08X refs=%d ===' % (nm, a, len(hits)))
    for h in hits[:4]:
        code = read_at(h - 0x40, 0x90)
        if not code:
            continue
        lines.append('  --- 0x%08X ---' % h)
        for n, ins in enumerate(md.disasm(code, h - 0x40)):
            mark = '  <<<' if ins.address <= h < ins.address + ins.size else ''
            lines.append('    %08X  %-18s %s %s%s'
                         % (ins.address, ins.bytes.hex(), ins.mnemonic,
                            ins.op_str, mark))
            if n > 18:
                break

open(os.path.join(OUT, 'scaleform_ready_refs.txt'), 'w',
     encoding='utf-8').write('\n'.join(lines) + '\n')
print()
print('详细 xref -> scaleform_ready_refs.txt')
