# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
def strings(lo,hi,minlen=6):
    out=[]; pat=re.compile(rb"[ -~]{%d,}"%minlen)
    for m in pat.finditer(C._img[lo:hi]): out.append((lo+m.start(),m.group().decode("latin1")))
    return out
for lo,hi,nm in [(0x864000,0x866000,"A 0x864-865"),(0x876800,0x877100,"B 0x8768"),
                 (0x7B1000,0x7B1C00,"C 0x7B1"),(0x37F000,0x380000,"D 0x37F"),
                 (0x6CB000,0x6CC200,"E 0x6CB-6CC"),(0x6D3000,0x6D8000,"F 0x6D3-6D8")]:
    print("=== %s ==="%nm)
    ss=strings(lo,hi)
    for a,st in ss[:18]: print("   0x%08X %r"%(a,st))
    if not ss: print("   (no strings)")
    print()
