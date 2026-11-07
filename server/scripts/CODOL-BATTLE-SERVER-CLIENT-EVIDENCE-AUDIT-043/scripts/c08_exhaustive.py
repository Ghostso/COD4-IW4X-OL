# -*- coding: utf-8 -*-
"""Phase C: exhaustive search for consumers of the net-buffer decoders:
  - direct E8 calls
  - imm32 data/vtable references (function pointers)
  - indirect call/jmp patterns
Read-only."""
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
def immrefs(t):
    va=C.IBI+t; pat=struct.pack("<I",va); rr=[]; i=0
    while True:
        j=b.find(pat,i)
        if j<0: break
        rr.append(j); i=j+1
    return rr
targets=[0x87A890,0x87AA40,0x87C110,0x87D5A0,0x87BE00,0x87BA50]
for t in targets:
    cs=callers(t); ir=immrefs(t)
    emit("target %08x : direct E8 callers=%s  imm32 refs=%s"%(
        t,[hex(x) for x in cs],[hex(x) for x in ir]))
emit("")
emit("=== function starts covering each direct caller ===")
def cc_starts(lo,hi):
    res=[]; i=lo
    while i<hi-2:
        if b[i]==0xCC and b[i+1]==0xCC and b[i+2]==0xCC:
            e=i
            while e<hi and b[e]==0xCC: e+=1
            res.append(e); i=e
        else: i+=1
    return res
allstarts=sorted(set(cc_starts(0x1000,0x8a8000)))
def fstart(rva):
    lo=0x1000
    for s in allstarts:
        if s<=rva: lo=s
        else: break
    return lo
for t in targets:
    for c in callers(t):
        emit("  %08x caller of %08x -> func %08x"%(c,t,fstart(c)))
io.open(os.path.join(C.EV,"c_consumer_exhaustive.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
