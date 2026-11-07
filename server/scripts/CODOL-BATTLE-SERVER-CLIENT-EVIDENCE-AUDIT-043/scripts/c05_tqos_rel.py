# -*- coding: utf-8 -*-
"""Phase C: relationships among 0x85D2E0 (TQOS ctor) / 0x85E9C0 (caller of dispatcher)
/ 0x85E6F0 (dispatcher); and .tp3/.tvm0/.tls exposure. Read-only."""
import sys, os, io, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._bi; out=[]
def emit(s): out.append(s)
def show(rva,n,label):
    emit("=== %s RVA=%08x ==="%(label,rva))
    for k in C.idis_range(rva,rva+n):
        emit("  %08x  %-16s %-8s %s"%(k.address-C.IBI,k.bytes.hex(),k.mnemonic,k.op_str))
show(0x85E9C0,0x80,"fn 0x85E9C0 (contains dispatcher caller 0x85EB16?)")
show(0x85EB50,0x60,"fn 0x85EB50 (tqos refs)")
# callers of the ctor and of dispatcher-containing family
def callers(t):
    tv=C.IBI+t; rr=[]; i=0x1000
    while i<0x8a8000-5:
        if b[i]==0xE8:
            rel=struct.unpack("<i",b[i+1:i+5])[0]
            if (C.IBI+i)+5+rel==tv: rr.append(i)
        i+=1
    return rr
emit("")
for t in (0x85D2E0,0x85E6F0,0x85E9C0,0x85EB50,0x85D5A0):
    emit("  callers of %08x : %s"%(t,[hex(x) for x in callers(t)]))
io.open(os.path.join(C.EV,"c_tqos_module_rel.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
