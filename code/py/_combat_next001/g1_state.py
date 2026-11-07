# -*- coding: utf-8 -*-
"""定位全局网络状态 0x76446B0 的写入点（这是"客户端是否进入战斗握手"的开关）。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
G = 0x076446B0

print("=== 写入 [0x76446B0] 的指令（mov dword ptr [imm32], imm/reg） ===")
hits = []
# c7 05 <imm32> <imm32>   mov dword [imm32], imm32
for o in pe.find_bytes(b"\xc7\x05" + struct.pack("<I", G)):
    va = pe.off_to_va(o)
    if va and pe.is_exec(va):
        imm = struct.unpack_from("<I", pe.data, o + 6)[0]
        hits.append(("movimm", va, imm))
# a3 <imm32>  mov [imm32], eax
for o in pe.find_bytes(b"\xa3" + struct.pack("<I", G)):
    va = pe.off_to_va(o)
    if va and pe.is_exec(va):
        hits.append(("mov eax", va, None))
# 89 05 <imm32> mov [imm32], eax
for o in pe.find_bytes(b"\x89\x05" + struct.pack("<I", G)):
    va = pe.off_to_va(o)
    if va and pe.is_exec(va):
        hits.append(("mov [..],eax", va, None))
# 89 0d / 89 15 / 89 1d ...
for pre, reg in ((b"\x89\x0d","ecx"),(b"\x89\x15","edx"),(b"\x89\x1d","ebx"),
                 (b"\x89\x35","esi"),(b"\x89\x3d","edi"),(b"\x89\x2d","ebp")):
    for o in pe.find_bytes(pre + struct.pack("<I", G)):
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            hits.append(("mov [" + reg + "]", va, None))
# 读取点 (8b 05 / 8b 0d ...) 也列出来
reads = []
for pre, reg in ((b"\x8b\x05","eax"),(b"\x8b\x0d","ecx"),(b"\x8b\x15","edx"),
                 (b"\x8b\x1d","ebx"),(b"\x8b\x35","esi"),(b"\x8b\x3d","edi")):
    for o in pe.find_bytes(pre + struct.pack("<I", G)):
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            reads.append(("%s<-[g]" % reg, va))

print("writes = %d" % len(hits))
for kind, va, imm in sorted(hits, key=lambda x: x[1]):
    print("   %08X  %-12s %s" % (va, kind, ("imm=%d (0x%X)" % (imm, imm)) if imm is not None else ""))
print()
print("reads = %d" % len(reads))
for kind, va in sorted(reads, key=lambda x: x[1])[:40]:
    print("   %08X  %s" % (va, kind))
