# -*- coding: utf-8 -*-
import sys,pickle,bisect,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E16_SOCKET_EVENT_GAME_SESSION_ATTRIBUTION_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E16_SOCKET_EVENT_GAME_SESSION_ATTRIBUTION_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
tv=0x400000+0x78772D
found=[]
for s in C.pe.sections:
    if s.SizeOfRawData==0: continue
    oo,_=C.off(s.VirtualAddress); raw=C.d[oo:oo+s.SizeOfRawData]
    for i in range(0,max(0,len(raw)-3)):
        if struct.unpack_from("<I",raw,i)[0]==tv:
            found.append((s.Name.rstrip(b'\0').decode(errors='replace'),s.VirtualAddress+i))
print("0x78772D dataptr refs:",found)
for t in (0x78772D,0x787780,0x787CD0):
    cs=sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
    print("  callers of 0x%06X: %s"%(t,[(hex(s),hex(f)) for s,k,f in cs][:8]))
# icmp/ws2 usage in 0x78772D
print("IAT refs in 0x78772D..0x787A2D:")
o2,_=C.off(0x78772D)
for ins in md.disasm(C.d[o2:o2+0x300],C.IB+0x78772D):
    for op in ins.operands:
        if op.type==X86_OP_MEM and 0xBAE000<=op.mem.disp<=0xBAE600:
            print("   0x%06X %s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
