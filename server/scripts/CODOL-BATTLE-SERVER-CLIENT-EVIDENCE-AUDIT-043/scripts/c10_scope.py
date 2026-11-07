# -*- coding: utf-8 -*-
"""Phase C: is 0x85D5A0 (deser2/read caller) part of the TQOS object created by
0x85EB50? Trace object identity via constructor/caller links. Read-only."""
import sys, os, io, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._bi; out=[]
def emit(s): out.append(s)
def callers(t):
    tv=C.IBI+t; rr=[]; i=0x1000
    while i<0x8a8000-5:
        if b[i]==0xE8:
            rel=struct.unpack("<i",b[i+1:i+5])[0]
            if (C.IBI+i)+5+rel==tv: rr.append(i)
        i+=1
    return rr
# 0x85EB50 calls 0x85D2E0 (ctor). 0x85D5A0 caller is 0x85DA5B (inside 0x85DA90?). verify.
for t in (0x85D5A0,0x85DA90,0x85D430,0x85D3A0,0x85E6F0):
    emit("callers of %08x : %s"%(t,[hex(x) for x in callers(t)]))
# what func contains 0x85DA5B?
def cc_starts(lo,hi):
    res=[]; i=lo
    while i<hi-2:
        if b[i]==0xCC and b[i+1]==0xCC and b[i+2]==0xCC:
            e=i
            while e<hi and b[e]==0xCC: e+=1
            res.append(e); i=e
        else: i+=1
    return res
st=sorted(set(cc_starts(0x85C000,0x85F000)))
def fs(r):
    lo=0x85C000
    for s in st:
        if s<=r: lo=s
        else: break
    return lo
emit("")
emit("0x85DA5B is in func %08x"%fs(0x85DA5B))
emit("0x85EB16 (dispatcher caller) is in func %08x"%fs(0x85EB16))
emit("0x85D96E is in func %08x"%fs(0x85D96E))
io.open(os.path.join(C.EV,"c_tqos_scope.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
