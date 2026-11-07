# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
def s(rva, ml=200):
    b=C.raw(rva,ml)
    if b is None: return None
    e=b.find(b"\x00"); return b[:e].decode("latin1","replace")
print("=== TQOS / QOS strings across image ===")
import re
pat = re.compile(rb"(?:[ -~]{4,})")
hits=[]
for m in pat.finditer(C._img):
    st=m.group().decode("latin1")
    if re.search(r"(?i)(tqos|qos[cs]|QOSCSPkg|QOSSSPkg|udp://|qos_)", st):
        hits.append((m.start(), st))
for a,st in hits[:200]:
    print("  0x%08X  %r"%(a,st))
print("total:",len(hits))
