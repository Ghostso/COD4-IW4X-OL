# -*- coding: utf-8 -*-
import sys,pickle,bisect,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t): return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
# Globals written by the two wrappers
print("0x6B4DE0 writes globals: 0xD47388/0xD4738C/0xD47398/0xD4739C")
print("0x784F60 writes globals: 0xD47370/0xD47374")
print()
# who reads those globals (nearby stat getters)
for g in ("0xd47388","0xd47370","0xd47374","0xd47398"):
    print("refs to [%s]:"%g)
    from sweep import sweep
    from capstone import *
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
    text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
    n=0
    for ins in sweep(md,text,base):
        if g in ins.op_str:
            print("   0x%06X (func 0x%06X) %s %s"%(ins.address-C.IB,fs(ins.address-C.IB),ins.mnemonic,ins.op_str)); n+=1
            if n>6: break
    print()
print("callers 0x6A9920:",[(hex(s),hex(f)) for s,k,f in callers(0x6A9920)][:6])
print("callers 0x6ABBC0:",[(hex(s),hex(f)) for s,k,f in callers(0x6ABBC0)][:6])
