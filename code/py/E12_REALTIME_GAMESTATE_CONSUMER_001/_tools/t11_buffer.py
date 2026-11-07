# -*- coding: utf-8 -*-
import sys,pickle,bisect,re
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
# who reads network into the buffer at +0x8048 (the 0x2ee0 = 12000 byte ring)
print("=== instructions referencing +0x8048 / +0x30af30 ===")
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
cnt=0
for ins in md.disasm(text,base):
    if ("0x8048" in ins.op_str or "0x30af30" in ins.op_str or "0x30af28" in ins.op_str):
        print("  %06X %-22s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str)); cnt+=1
        if cnt>60: break
