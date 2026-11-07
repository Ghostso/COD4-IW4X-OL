# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== accepted/common path: 0x632736 .. 0x6327A0 (does it set esi or ecx?) ===")
for l in pe.dis(0x632736, 45):
    print(l)
print()
print("=== who calls 0x62F840? ===")
c = pe.calls_to(0x62F840)
print("direct callers =", len(c))
for v in c:
    print("   %08X" % v)
print()
print("=== is 0x62F840 referenced as data (vtable slot)? ===")
for o in pe.find_bytes(struct.pack("<I", 0x62F840)):
    v = pe.off_to_va(o)
    print("   fileoff=%08X va=%s" % (o, hex(v) if v else "-"))
