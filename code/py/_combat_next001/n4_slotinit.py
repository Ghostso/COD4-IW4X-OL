# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x62CD30 (reservation slot initializer) full ===")
for l in pe.dis(0x62CD30, 60):
    print(l)
print()
print("=== callers of 0x62CD30 ===")
for v in pe.calls_to(0x62CD30):
    print("   %08X" % v)
print()
print("=== all writes of immediate 0x6EF0 (the slot size) ===")
for o in pe.find_bytes(b"\x68\xf0\x6e\x00\x00"):
    v = pe.off_to_va(o)
    if v and pe.is_exec(v):
        print("   push 0x6EF0 at %08X" % v)
