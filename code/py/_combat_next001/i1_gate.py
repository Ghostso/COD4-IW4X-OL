# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== accepted handler 0x632680: gates and the two 'wrong path' targets ===")
for l in pe.dis(0x632876, 22):
    print(l)
print()
print("=== target 0x632916 (reached when A/B mismatch) ===")
for l in pe.dis(0x632916, 6):
    print(l)
print()
print("=== is 0x6293B0 reachable only from 0x63285A? ===")
for va in pe.calls_to(0x6293B0):
    print("   caller %08X" % va)
print()
print("=== callers of the accepted handler entry (find its vtable/registration) ===")
# 找 0x632680 的引用
for o in pe.find_bytes(struct.pack("<I", 0x632680)):
    v = pe.off_to_va(o)
    sec = pe.section_of(v) if v else None
    print("   raw ref fileoff=%08X va=%s sect=%s" % (o, hex(v) if v else "-", sec.name if sec else "-"))
