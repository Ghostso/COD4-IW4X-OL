# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
R = "eax ecx edx ebx esp ebp esi edi".split()

print("=== call dword ptr [reg+0x13C] (disp32 form) ===")
n = 0
for o in range(len(d) - 7):
    if d[o] != 0xFF: continue
    m = d[o+1]
    if (m & 0x38) != 0x10: continue
    if (m >> 6) != 2 or (m & 7) == 4: continue
    if struct.unpack_from("<i", d, o+2)[0] != 0x13C: continue
    va = pe.off_to_va(o)
    if va and pe.is_exec(va):
        n += 1
        print("   %08X  call [%s+0x13C]" % (va, R[m & 7]))
print("   total =", n)

print()
print("=== 0x7F153F (mmbook local dispatcher) 所在函数 0x7F110F 的尾部/参数 ===")
print("   已知: 0x7F155A mov eax,[ecx] / 0x7F155C mov eax,[eax+0x13C] / 0x7F156F call eax")
print()
print("=== vtable 基址一致性 ===")
for slot_va, name in ((0xDC73B0, "0x632680 (accepted)"), (0xDC72B8, "0x62CD30 (slot filler)"),
                      (0xDC72B0, "0x62F840 (booking entry)"), (0xDC7274, "0x6391E0 (slot 0)")):
    off = slot_va - 0xDC7274
    print("   %-24s at vtable+0x%03X  (primary vtable base 0xDC7274)" % (name, off))
