# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x62BFFF (writes BOTH slot count +0x7230 and index +0xE360) ===")
for l in pe.dis(0x62BFFF, 70):
    print(l)
print()
print("=== callers of 0x62BFFF ===")
for v in pe.calls_to(0x62BFFF):
    print("   %08X" % v)
print()
print("=== data-refs of 0x62BFFF ===")
import struct
for o in pe.find_bytes(struct.pack("<I", 0x62BFFF)):
    v = pe.off_to_va(o)
    print("   fileoff=%08X va=%s" % (o, hex(v) if v else "-"))
