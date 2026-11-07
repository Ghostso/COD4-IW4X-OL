import pefile, math, collections, os
p=r"COD OL\codoMP_client_shipRetailBase.dll"
pe=pefile.PE(p)
d=open(p,"rb").read()
print("=== Base.dll 区段与熵 ===")
for s in pe.sections:
    nm=s.Name.rstrip(b"\x00").decode("latin1")
    seg=d[s.PointerToRawData:s.PointerToRawData+max(s.SizeOfRawData,0)][:0x20000]
    if seg:
        c=collections.Counter(seg); tot=len(seg)
        ent=-sum((v/tot)*math.log2(v/tot) for v in c.values()); z=seg.count(0)/tot
    else: ent=0; z=0
    print("  %-9s VA 0x%08X vsize 0x%-8X raw 0x%-7X rsize 0x%-7X ent %.2f zeros %.2f"%(nm,s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData,ent,z))
print()
# 反汇编 .text 开头看是否有效
from capstone import *
md=Cs(CS_ARCH_X86, CS_MODE_32)
t=[s for s in pe.sections if b".text" in s.Name or b".tls" in s.Name]
for s in t[:2]:
    nm=s.Name.rstrip(b"\x00").decode("latin1")
    off=s.PointerToRawData
    print("---- %s @ VA 0x%08X 前 12 条 ----"%(nm, pe.OPTIONAL_HEADER.ImageBase+s.VirtualAddress))
    n=0
    for ins in md.disasm(d[off:off+40], pe.OPTIONAL_HEADER.ImageBase+s.VirtualAddress):
        print("   %08X  %-18s %s %s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)); n+=1
        if n>=12: break
