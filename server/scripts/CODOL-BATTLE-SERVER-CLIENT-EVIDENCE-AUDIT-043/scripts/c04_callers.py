# -*- coding: utf-8 -*-
"""Phase C: attribute the callers of the net-buffer decoders. Read-only."""
import sys, os, io, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._bi; out=[]
def emit(s): out.append(s)
def cc_starts(lo,hi):
    res=[]; i=lo
    while i<hi-2:
        if b[i]==0xCC and b[i+1]==0xCC and b[i+2]==0xCC:
            e=i
            while e<hi and b[e]==0xCC: e+=1
            res.append(e); i=e
        else: i+=1
    return res
# function starts in the caller region
starts=cc_starts(0x85C000,0x85F000)
def fn_containing(rva):
    lo=0x85C000
    for s in starts:
        if s<=rva: lo=s
        else: break
    return lo
callers=[0x85D49D,0x85D3DB,0x85D418,0x85D9B5,0x85D9F7,0x85D96E,0x85E71A]
emit("=== caller attribution (net-buffer decoders + read primitive) ===")
for c in callers:
    emit("  caller %08x  in func %08x"%(c, fn_containing(c)))
emit("")
emit("=== all function starts in 0x85D000..0x85F000 ===")
for s in starts:
    if 0x85D000<=s<=0x85F000: emit("  %08x"%s)
emit("")
# Which of these functions reference TQOS strings?
tqos=[0x985AA4,0x985A94,0x985A84,0x985A78,0x985A68,0x985A58,0x985AB0,0x985AE0,0x985B1C]
tqos_refs=set()
code=b[0x1000:0x8a8000]
for r in tqos:
    va=C.IBI+r; pat=struct.pack("<I",va); i=0
    while True:
        j=code.find(pat,i)
        if j<0: break
        tqos_refs.add(fn_containing(0x1000+j)); i=j+1
emit("=== functions (from above set) that reference TQOS strings ===")
for f in sorted(tqos_refs): emit("  %08x"%f)
# Also print the object ctor 0x85D2E0 and where 0x85D49D sits
emit("")
emit("=== is 0x85D49D inside the TQOS-object family (0x85D2E0 ctor)? ===")
emit("  0x85D2E0 ctor func start=%08x ; 0x85D49D func start=%08x"%(
    fn_containing(0x85D2E0), fn_containing(0x85D49D)))
io.open(os.path.join(C.EV,"c_caller_attribution.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
