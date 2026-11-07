# -*- coding: utf-8 -*-
import sys,pickle,bisect,collections,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
print("=== direct callers of 0x3524F0 (write side) ===")
for s,k,f in sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==0x3524F0)):
    print("   site 0x%06X %s in 0x%06X"%(s,k,f))
print()
print("=== data pointers to 0x3524F0 (VA 0x7524F0) ===")
tv=0x400000+0x3524F0
for sec in C.pe.sections:
    if sec.SizeOfRawData==0: continue
    o,_=C.off(sec.VirtualAddress)
    raw=C.d[o:o+sec.SizeOfRawData]
    for i in range(0,max(0,len(raw)-3)):
        if struct.unpack_from("<I",raw,i)[0]==tv:
            print("   %s RVA 0x%X (func 0x%06X)"%(sec.Name.rstrip(b'\0').decode(errors='replace'),sec.VirtualAddress+i,fs(sec.VirtualAddress+i)))
print()
print("=== all .text refs to +0x30AF2C (write cursor) ===")
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
for ins in sweep(md,text,base):
    if "0x30af2c" in ins.op_str:
        print("   0x%06X (func 0x%06X) %s %s"%(ins.address-C.IB,fs(ins.address-C.IB),ins.mnemonic,ins.op_str))
