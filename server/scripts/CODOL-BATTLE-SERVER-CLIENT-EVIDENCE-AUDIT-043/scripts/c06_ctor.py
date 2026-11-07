# -*- coding: utf-8 -*-
"""Confirm: 0x85EB50 (tqos_create_protohandle) constructs the TQOS object whose method
family contains the dispatcher 0x85E6F0 and the net-buffer callers. Read-only."""
import sys, os, io, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._bi; out=[]
def emit(s): out.append(s)
def show(rva,n,label):
    emit("=== %s RVA=%08x ==="%(label,rva))
    for k in C.idis_range(rva,rva+n):
        emit("  %08x  %-16s %-8s %s"%(k.address-C.IBI,k.bytes.hex(),k.mnemonic,k.op_str))
# what does 0x85EB50 call / store around ctor call at 0x85EBBB?
show(0x85EBA8,0x30,"0x85EBA8 (ctor call site)")
# does the dispatcher family's object (esi in 0x85E6F0) get its buffer from the tqos ctor?
# Check 0x85D5A0 (net-buffer caller) attr: it references tqos strings -> yes
code=b[0x1000:0x8a8000]
def refs(rva):
    va=C.IBI+rva; pat=struct.pack("<I",va); rr=[]; i=0
    while True:
        j=code.find(pat,i)
        if j<0: break
        rr.append(0x1000+j); i=j+1
    return rr
emit("")
emit("=== 0x85D5A0 references tqos string? ===")
for r in (0x985A78,0x985A68,0x985A58,0x985AB0,0x985B38,0x985B1C,0x985AF0,0x985AE0):
    s=C.icstr(r,30)
    emit("  %08x %-26s refs=%s"%(r,(s or b"").decode('latin1','replace'),[hex(x) for x in refs(r) if 0x85d000<=x<0x85f000]))
io.open(os.path.join(C.EV,"c_tqos_ctor_rel.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
