# -*- coding: utf-8 -*-
"""Phase B: independent instruction-level audit of 0x87A890 (sizeinfo/length helper).
Read-only."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
out=[]
def emit(s): out.append(s); 
def dis(rva,end):
    for i in C.idis_range(rva,end):
        emit("  %08x  %-18s %-8s %s"%(i.address-C.IBI, i.bytes.hex(), i.mnemonic, i.op_str))
        yield i

emit("=== 0x87A890 full function (to first int3-pad after 0x87A980) ===")
# find end: first cc-pad run after 0x87A890
b=C._bi; i=0x87A890
end=0x87AB00
while i<end-2:
    if b[i]==0xCC and b[i+1]==0xCC and b[i+2]==0xCC:
        end=i; break
    i+=1
emit("(end at %08x)"%end)
for _ in dis(0x87A890, end): pass
io.open(os.path.join(C.EV,"dis_87A890_full.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("wrote dis_87A890_full.txt  (%d lines)"%len(out))
print("\n".join(out))
