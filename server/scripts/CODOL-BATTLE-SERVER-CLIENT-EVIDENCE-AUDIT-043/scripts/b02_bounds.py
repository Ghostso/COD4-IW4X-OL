# -*- coding: utf-8 -*-
"""Phase B: exact function boundaries in the 0x87A8xx sizeinfo region, plus the
semantics of helpers 0xB44B20 and 0xBCD790. Read-only."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._bi
out=[]
def emit(s): out.append(s)

emit("=== cc-padding / ret boundaries in 0x87A800..0x87AC00 ===")
i=0x87A800
while i<0x87AC00-3:
    if b[i]==0xC3:
        # ret; check trailing bytes before next
        j=i+1; pad=0
        while j<0x87AC00 and b[j] in (0xCC,0xC3):
            if b[j]==0xCC: pad+=1
            j+=1
        emit("  ret at %08x  next-start-guess %08x  pad=%d  nextbytes=%s"%(i,j,pad,b[j:j+6].hex()))
    i+=1

for f,label in ((0x87A890,"F-A"),(0x87AA40,"F-B")):
    emit("")
    emit("=== %s at %08x : boundary probe ==="%(label,f))
    ins=C.idis_at(f,15)
    emit("  prologue: %s %s"%(ins.mnemonic,ins.op_str))
    # find its ret by linear decode
    end=f
    for k in C.idis_range(f, min(f+0x400,0x87AC00)):
        if k.mnemonic=="ret":
            emit("  first ret at %08x (offset +0x%x)"%(k.address-C.IBI, k.address-C.IBI-f))
            break

emit("")
emit("=== helper 0xB44B20 (called by F-A at 0x87A8AD) ===")
for k in C.idis_range(0xB44B20, 0xB44B90):
    emit("  %08x  %-16s %-8s %s"%(k.address-C.IBI,k.bytes.hex(),k.mnemonic,k.op_str))
emit("")
emit("=== helper 0xBCD790 (called by F-A at 0x87A8C1 / 0x87A9AF) ===")
for k in C.idis_range(0xBCD790, 0xBCD820):
    emit("  %08x  %-16s %-8s %s"%(k.address-C.IBI,k.bytes.hex(),k.mnemonic,k.op_str))
io.open(os.path.join(C.EV,"dis_87A8xx_boundaries.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
