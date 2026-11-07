# -*- coding: utf-8 -*-
"""A: 查找 [reg+4] 的写入点（listener 链表注册候选）。"""
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE

pe = PE.load()

def scan_writes(disp):
    """mov [reg+disp], reg 形式: 89 /r，modrm.mod=01 (disp8) 或 10 (disp32)。"""
    hits = collections.Counter()
    for o in range(len(pe.data) - 4):
        if pe.data[o] != 0x89:
            continue
        modrm = pe.data[o + 1]
        mod = modrm >> 6
        rm = modrm & 7
        if rm == 4:   # SIB，跳过（本分析不用）
            continue
        if mod == 1:
            d = struct.unpack_from("<b", pe.data, o + 2)[0]
            size = 3
        elif mod == 2:
            d = struct.unpack_from("<i", pe.data, o + 2)[0]
            size = 6
        else:
            continue
        if d != disp:
            continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            hits[(rm, size)] += 1
    return hits

print("=== mov [reg+4], reg 写入点统计 (rm, 指令长度) ===")
for k, v in sorted(scan_writes(4).items()):
    print("  rm=%d len=%d count=%d" % (k[0], k[1], v))

print()
print("=== 在 0x620000..0x640000 区间内，所有 mov [reg+4],reg 的具体地址 ===")
out = []
for o in range(len(pe.data) - 6):
    if pe.data[o] != 0x89:
        continue
    modrm = pe.data[o + 1]
    mod = modrm >> 6; rm = modrm & 7
    if rm == 4: continue
    if mod == 1: d = struct.unpack_from("<b", pe.data, o + 2)[0]
    elif mod == 2: d = struct.unpack_from("<i", pe.data, o + 2)[0]
    else: continue
    if d != 4: continue
    va = pe.off_to_va(o)
    if va and pe.is_exec(va) and 0x620000 <= va < 0x640000:
        src = (modrm >> 3) & 7
        out.append((va, rm, src))
print("count in range = %d" % len(out))
for va, rm, src in out[:60]:
    print("  %08X  mov [%s+4], %s" % (va, "eax ecx edx ebx esp ebp esi edi".split()[rm],
                                      "eax ecx edx ebx esp ebp esi edi".split()[src]))
