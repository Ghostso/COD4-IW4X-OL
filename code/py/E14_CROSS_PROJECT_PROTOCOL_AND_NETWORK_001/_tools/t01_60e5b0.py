# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
print("=== func containing 0x60E5B0 ===")
print("  0x60E5B0 in func 0x%06X"%fs(0x60E5B0))
print()
print("=== callers of 0x60E5B0 ===")
for s,k,f in sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==0x60E5B0)):
    print("   site 0x%06X %s in 0x%06X"%(s,k,f))
print()
print("=== all refs to [ebp-0xd2c] ===")
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
n=0
for ins in sweep(md,text,base):
    if "ebp - 0xd2c" in ins.op_str:
        print("   %06X (func 0x%06X) %s %s"%(ins.address-C.IB,fs(ins.address-C.IB),ins.mnemonic,ins.op_str)); n+=1
print("total:",n)
