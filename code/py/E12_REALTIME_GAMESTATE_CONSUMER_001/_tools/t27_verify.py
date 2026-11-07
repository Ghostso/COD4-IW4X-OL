# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t):
    return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
print("=== callers of 0x1AC190 MSG_InitReadOnly ===")
for s,k,f in callers(0x1AC190):
    print("   site 0x%06X %s in 0x%06X"%(s,k,f))
print()
print("=== callers of 0x74F090 demo reader (as direct call) ===")
for s,k,f in callers(0x74F090):
    print("   site 0x%06X %s in 0x%06X"%(s,k,f))
print()
print("=== all mov [X+0x89244], imm sites (reader install) ===")
from sweep import sweep
from capstone.x86 import *
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
for ins in sweep(md,text,base):
    if "0x89244]" in ins.op_str and ins.mnemonic=="mov" and ins.op_str.split(",")[0].strip().endswith("0x89244]"):
        print("   %06X %s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
