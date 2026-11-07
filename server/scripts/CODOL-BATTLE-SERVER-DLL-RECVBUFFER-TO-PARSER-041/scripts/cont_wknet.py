# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
b=C._b
def region_strings(lo, hi, minlen=3):
    o=C.rva2off(lo); e=C.rva2off(hi); out=[]; cur=bytearray(); start=0
    for i in range(o,e):
        ch=b[i]
        if 0x20<=ch<0x7f:
            if not cur: start=i
            cur.append(ch)
        else:
            if len(cur)>=minlen:
                r=C.off2rva(start); out.append((r,cur.decode("latin1")))
            cur=bytearray()
    return out
print("=== .rdata 0x922000..0x926000 (WKNet_ context) ===")
for r,s in region_strings(0x922000,0x926000,3):
    print("  0x%08X  %r" % (r,s[:100]))
