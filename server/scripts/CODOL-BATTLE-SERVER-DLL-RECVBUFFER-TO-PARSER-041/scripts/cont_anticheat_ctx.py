# -*- coding: utf-8 -*-
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
b=C._b

# dump .rdata region around 0x958000..0x959700 as strings for context
def region_strings(lo, hi, minlen=4):
    o=C.rva2off(lo); e=C.rva2off(hi)
    out=[]; cur=bytearray(); start=0
    for i in range(o, e):
        ch=b[i]
        if 0x20<=ch<0x7f:
            if not cur: start=i
            cur.append(ch)
        else:
            if len(cur)>=minlen:
                r=C.off2rva(start); out.append((r, cur.decode("latin1")))
            cur=bytearray()
    return out
print("=== .rdata strings 0x956000..0x959700 ===")
for r,s in region_strings(0x956000,0x959700,4):
    print("  0x%08X  %r" % (r, s[:110]))
