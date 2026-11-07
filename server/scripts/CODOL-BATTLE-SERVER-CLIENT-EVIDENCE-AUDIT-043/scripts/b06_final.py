# -*- coding: utf-8 -*-
"""Phase B/C final checks: characterize [ebx]/[ebx+8] in 0x87C110; confirm the two
entries are distinct; enumerate imm32 call/target census. Read-only."""
import sys, os, io, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._bi; out=[]
def emit(s): out.append(s)
def show(rva,n,label):
    emit("=== %s RVA=%08x ==="%(label,rva))
    for k in C.idis_range(rva,rva+n):
        emit("  %08x  %-16s %-8s %s"%(k.address-C.IBI,k.bytes.hex(),k.mnemonic,k.op_str))
show(0x87C740,0xF0,"0x87C740.. (uses [ebx+8])")
# distinctness
emit("")
emit("=== does 0x87C110 body call/fall into 0x87D5A0 or vice versa? ===")
for lo,hi,lab in [(0x87C110,0x87D593,"0x87C110"),(0x87D5A0,0x87ED58,"0x87D5A0")]:
    tgt=[]
    for k in C.idis_range(lo,hi):
        if k.mnemonic in ("call","jmp"):
            t=C.target_of(k)
            if t is not None:
                tr=t-C.IBI
                if (lab=="0x87C110" and 0x87D5A0<=tr<0x87ED58) or (lab=="0x87D5A0" and 0x87C110<=tr<0x87D593):
                    tgt.append((k.address-C.IBI,k.mnemonic,hex(tr)))
    emit("  %s -> other: %s"%(lab,tgt))
io.open(os.path.join(C.EV,"b_final_checks.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
