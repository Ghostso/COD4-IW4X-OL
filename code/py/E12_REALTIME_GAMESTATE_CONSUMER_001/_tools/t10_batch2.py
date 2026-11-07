# -*- coding: utf-8 -*-
import sys,pickle,bisect,struct,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None

print("=== strings ===")
for va in (0xCD6384,0xCD6328,0xCD637C,0xCD6360,0xCD63A0):
    b=C.bytes_rva(va-C.IB,96)
    print("  0x%X %r"%(va,(b.split(b"\0")[0] if b else None)))

print()
print("=== direct callers of 0xA2E50 / 0xA2D91 / 0xA2660 ===")
for t in (0xA2E50,0xA2D91,0xA2660,0xA2480):
    cs=sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
    print("  0x%06X : %d"%(t,len(cs)))
    for s,k,f in cs: print("      site 0x%06X %s in 0x%06X"%(s,k,f))

print()
print("=== data pointers to 0xA2E50 (VA 0x4A2E50) ===")
tv=0x400000+0xA2E50
found=[]
for s in C.pe.sections:
    if s.SizeOfRawData==0: continue
    o,_=C.off(s.VirtualAddress)
    raw=C.d[o:o+s.SizeOfRawData]
    for i in range(0,max(0,len(raw)-3)):
        if struct.unpack_from("<I",raw,i)[0]==tv:
            found.append((s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress+i))
print("  count",len(found))
for sec,rva in found[:20]: print("     %s 0x%X"%(sec,rva))
