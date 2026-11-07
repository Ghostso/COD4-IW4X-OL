# -*- coding: utf-8 -*-
"""用主 vtable 0xDC7274 定位 slot 派发：call [reg+0x04] / call [reg+0x08]。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
R = "eax ecx edx ebx esp ebp esi edi".split()

def scan_call_disp(disp):
    out = []
    for o in range(len(d) - 4):
        if d[o] != 0xFF: continue
        m = d[o+1]
        if (m & 0x38) != 0x10: continue      # /2 call
        if (m >> 6) != 1: continue           # mod=01 disp8
        rm = m & 7
        if rm in (4, 5): continue            # 排除 SIB 与 [ebp+disp]（栈帧）
        if d[o+2] != disp: continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va): out.append((va, R[rm]))
    return out

for disp in (0x04, 0x08):
    hits = scan_call_disp(disp)
    print("=== call dword ptr [reg+0x%02X]  (排除 ebp/SIB) : %d 处 ===" % (disp, len(hits)))
    for va, reg in hits:
        print("   %08X  call [%s+0x%02X]" % (va, reg, disp))
    print()

print("=== 另外：0xDC7274 主 vtable 里是否有 0x632680 / 0x6293B0 ? ===")
for i in range(0, 0x60):
    va = 0xDC7274 + i*4
    v = struct.unpack("<I", pe.read(va, 4))[0]
    if v in (0x632680, 0x6293B0, 0x6292B0, 0x6376F0, 0x637590, 0x637720):
        print("   %08X slot +0x%03X = %08X" % (va, i*4, v))
print("   (0xDC72B0 起 = vtable+0x3C，其上含 0x62F840/+0x3C、0x62CD30/+0x44)")
