# -*- coding: utf-8 -*-
"""a21: identify the network clusters by nearby strings."""
import sys, os, struct, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
def strs_in(lo,hi,minlen=4):
    out=[]
    pat=re.compile(rb"[ -~]{%d,}"%minlen)
    for m in pat.finditer(C._img[lo:hi]):
        out.append((lo+m.start(), m.group().decode("latin1")))
    return out
for lo,hi,nm in [(0x865380,0x865900,"cluster A 0x865xxx"),(0x876850,0x877000,"cluster B 0x8768xx"),
                 (0x7B1000,0x7B1A00,"cluster C 0x7B1xxx"),(0x37F000,0x380000,"cluster D 0x37Fxxx")]:
    print("=== %s strings (target strings only) ==="%nm)
    for a,st in strs_in(lo,hi,6):
        if re.search(r"(?i)(timeout|time-out|connect|socket|refused|host|proxy|http|ssl|tls|cert|recv|send|bind|port|peer|curl|trying|resolv)", st):
            print("   0x%08X %r"%(a,st))
    print()
