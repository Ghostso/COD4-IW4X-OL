# -*- coding: utf-8 -*-
import sys,re,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t): return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
print("=== 0x60C8A0 (HTTP keepalive ref) ===")
for s,k,f in callers(0x60C8A0)[:8]: print("   caller 0x%06X in 0x%06X"%(s,f))
o,_=C.off(0x60CE00)
for ins in md.disasm(C.d[o:o+0x40],C.IB+0x60CE00):
    print("   %06X %-16s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
print()
print("=== 0x6B3840 (GET ref) ===")
for s,k,f in callers(0x6B3840)[:8]: print("   caller 0x%06X in 0x%06X"%(s,f))
o2,_=C.off(0x6B3860)
for ins in md.disasm(C.d[o2:o2+0x40],C.IB+0x6B3860):
    print("   %06X %-16s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
print()
print("=== libcurl strings ===")
for s in C.pe.sections:
    if s.SizeOfRawData==0: continue
    o4,_=C.off(s.VirtualAddress); raw=C.d[o4:o4+s.SizeOfRawData]
    for m in list(re.finditer(rb"libcurl[ -~]{0,60}",raw))[:5]:
        print("   0x%X %r"%(C.IB+s.VirtualAddress+m.start(),m.group()[:70]))
