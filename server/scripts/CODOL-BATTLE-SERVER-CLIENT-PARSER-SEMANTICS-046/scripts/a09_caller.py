# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
def s(rva, ml=300):
    b=C.raw(rva,ml)
    if b is None: return None
    e=b.find(b"\x00"); return b[:e].decode("latin1","replace")
def strs_in(lo,hi):
    out=[]
    for i in range(lo,hi-4):
        if C._img[i]==0x68:
            v=struct.unpack_from("<I",C._img,i+1)[0]
            if 0x900000<=v<0xE00000:
                st=s(v-IB)
                if st and all(32<=ord(c)<127 for c in st[:3]): out.append((i,v,st))
    return out
print("=== function containing 0x85EB16 / 0x85EC01 ===")
print(C.dump(0x85EB00, 0x85EE40))
