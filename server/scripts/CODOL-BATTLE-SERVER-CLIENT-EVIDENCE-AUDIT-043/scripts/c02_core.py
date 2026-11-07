# -*- coding: utf-8 -*-
"""Phase C: shared core 0x87ED70; read-primitive reachability via thunk 0x87BA50;
varint helper 0xBCD790 semantics. Read-only."""
import sys, os, io, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._bi; out=[]
def emit(s): out.append(s)
def show(rva,n,label):
    emit("=== %s RVA=%08x ==="%(label,rva))
    for k in C.idis_range(rva,rva+n):
        emit("  %08x  %-16s %-8s %s"%(k.address-C.IBI,k.bytes.hex(),k.mnemonic,k.op_str))
show(0x87BA50,0x10,"thunk 0x87BA50")
show(0x87ED70,0x50,"shared core 0x87ED70")
show(0x87EDB0,0x30,"core 0x87EDB0")
show(0xBCD790,0x30,"varint width 0xBCD790")
show(0xBCD7C0,0x70,"varint decode 0xBCD7C0")
# read primitive reachability: callers of thunk
emit("")
def callers(t):
    tv=C.IBI+t; rr=[]; i=0x1000
    while i<0x8a8000-5:
        if b[i]==0xE8:
            rel=struct.unpack("<i",b[i+1:i+5])[0]
            if (C.IBI+i)+5+rel==tv: rr.append(i)
        i+=1
    return rr
for t in (0x87BA50,0x87BE00):
    emit("  callers of %08x : %s"%(t,[hex(x) for x in callers(t)]))
io.open(os.path.join(C.EV,"c_shared_core_and_varint.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
