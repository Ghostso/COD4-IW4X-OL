# -*- coding: utf-8 -*-
import sys, pickle, bisect
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fstart(r):
    i=bisect.bisect_right(prologues,r)-1; return prologues[i] if i>=0 else None
callees={}
for s,k,t in edges:
    callees.setdefault(s,[]).append((k,t))
imms=set()
for s,k,t in edges:
    imms.add(t)
print("total unique call/jmp targets:", len(imms))
# find all references to key primitives
TARGETS={0x1AC670:"MSG_ReadBits",0x1AC1D0:"MSG_ReadData",0xA2660:"cfg_body",0xA2480:"A3",0x352E80:"cfg_writer?",0x3512A0:"cfg_path1"}
for tgt,name in TARGETS.items():
    hits=sorted(set((s,k,fstart(s)) for s,k,t in edges if t==tgt))
    print("\n=== %s 0x%X : %d sites ==="%(name,tgt,len(hits)))
    for s,k,f in hits[:60]:
        print("   site 0x%X %-4s in 0x%X"%(s,k,f))
