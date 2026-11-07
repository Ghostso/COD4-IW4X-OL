# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

for name, a in (("0x62B640 (sets +0x278=1)", 0x62B640),
                ("0x62F2CF (resets +0x278=0?)", 0x62F2CF),
                ("0x63735F (reader)", 0x63735F)):
    print("=== callers of %s ===" % name)
    c = pe.calls_to(a)
    print("   direct = %d" % len(c))
    for v in c[:12]:
        print("      %08X" % v)
    # vtable refs
    tot = 0
    for o in pe.find_bytes(struct.pack("<I", a)):
        v = pe.off_to_va(o)
        if v:
            tot += 1
            if tot <= 6:
                print("      data-ref va=%s" % hex(v))
    print("   data-refs = %d" % tot)
    print()
