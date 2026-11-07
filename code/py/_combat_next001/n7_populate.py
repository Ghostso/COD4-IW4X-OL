# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

for name, a in (("0x637590", 0x637590), ("0x637720", 0x637720), ("0x6376F0", 0x6376F0),
                ("0x62CD30", 0x62CD30), ("0x62C0C7 fn", 0x62C080)):
    print("=== callers of %s ===" % name)
    c = pe.calls_to(a)
    print("   direct=%d" % len(c))
    for v in c[:10]:
        print("      %08X" % v)
    print()

print("=== 0x6379B0 region (lea edi,[ebx+0x7470]) ===")
for l in pe.dis(0x637980, 35):
    print(l)
