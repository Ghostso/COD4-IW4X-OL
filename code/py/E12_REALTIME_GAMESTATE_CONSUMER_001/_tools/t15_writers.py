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
# The ring buffer at +0x8048 belongs to structure at [0x743de9c]. Let's see what writes 0x743de9c.
print("=== writers of [0x743de9c] ===")
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
from sweep import sweep
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
for ins in sweep(md,text,base):
    if "0x743de9c" in ins.op_str and ins.mnemonic in ("mov","lea") and "," in ins.op_str:
        left=ins.op_str.split(",")[0].strip()
        if left.startswith("dword ptr [0x743de9c]") or left=="dword ptr [0x743de9c]":
            print("  %06X %-22s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
