# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x7F43C0 (called at 0x62DD8B, sibling of 0x7F44B0) ===")
for l in pe.dis(0x7F43C0, 60):
    print(l)
print()
print("=== callers of 0x7F43C0 ===")
c = pe.calls_to(0x7F43C0)
print("   count = %d" % len(c))
for v in c[:20]:
    print("      %08X" % v)
print()
print("=== 0x62DD5F function FULL (who calls it?) ===")
for l in pe.dis(0x62DD5F, 12):
    print(l)
print()
for v in pe.calls_to(0x62DD5F):
    print("   caller %08X" % v)
import struct
print("   data-refs:", [hex(pe.off_to_va(o)) for o in pe.find_bytes(struct.pack("<I", 0x62DD5F))])
