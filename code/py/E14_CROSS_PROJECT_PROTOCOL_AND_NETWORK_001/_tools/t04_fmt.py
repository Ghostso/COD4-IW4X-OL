# -*- coding: utf-8 -*-
import sys,struct,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
out=[]
out.append("### 0x60E5B0 format-specifier handling (0x60E660..0x60EA00)")
o,_=C.off(0x60E660)
for ins in md.disasm(C.d[o:o+0x3A0],C.IB+0x60E660):
    out.append("  %06X %-20s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
out.append("")
out.append("### callers of 0x6029A0 (recv wrapper) + upstream")
for s,k,f in sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==0x6029A0)):
    out.append("  site 0x%06X %s in 0x%06X"%(s,k,f))
for s,k,f in sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==0x602760)):
    pass
out.append("")
out.append("### vtable-region: scan .text for immediates pointing to 0x775940/0x775A00/0x775A50/0x775AB0/0x775AF0")
targets={0x400000+v for v in (0x775940,0x775A00,0x775A50,0x775AB0,0x775AF0,0x775B30,0x775B70)}
sec=C.pe.sections[0]; o2,_=C.off(sec.VirtualAddress)
text=C.d[o2:o2+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
import struct as st
for p in range(0,len(text)-4):
    v=st.unpack_from("<I",text,p)[0]
    if v in targets:
        out.append("   raw 0x%06X imm VA 0x%X (func 0x%06X)"%(base+p-C.IB,v,fs(base+p-C.IB)))
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_data\out_fmt_vtable.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out[:120]))
