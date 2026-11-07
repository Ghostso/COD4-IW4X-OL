# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== 0xDC7274 .. 0xDC72E0 (from the vtable written by the constructor) ===")
for i in range(0, (0xDC72E0 - 0xDC7274)//4):
    va = 0xDC7274 + i*4
    v = struct.unpack("<I", pe.read(va, 4))[0]
    mark = ""
    if v == 0x632680: mark = "  <- accepted handler"
    print("   %08X  [%2d]  %08X%s" % (va, i, v, mark))
print()
print("=== key question: where does 0xDC72B0 sit relative to 0xDC7274? ===")
print("   0xDC72B0 - 0xDC7274 = 0x%X = %d dwords = %d slots" % (0xDC72B0-0xDC7274, (0xDC72B0-0xDC7274)//4, (0xDC72B0-0xDC7274)//4))
print()
print("=== does 0xDC7274 slot 0 hold 0x62F840 (like 0xDC72B0 slot 0)? ===")
for base, nm in ((0xDC7274, "constructor-written"), (0xDC72B0, "NEXT-001-claimed")):
    s0 = struct.unpack("<I", pe.read(base, 4))[0]
    print("   %s 0x%08X slot0 = %08X" % (nm, base, s0))
