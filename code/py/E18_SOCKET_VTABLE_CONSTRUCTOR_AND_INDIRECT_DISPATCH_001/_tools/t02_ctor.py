# -*- coding: utf-8 -*-
import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
lo=0x400000+0x898568; hi=0x400000+0x898634
print("=== .text immediate refs into vtable range 0x898568..0x898634 ===")
n=0
for ins in sweep(md,text,base):
    for op in ins.operands:
        if op.type==X86_OP_IMM and lo<=op.imm<=hi+4:
            print("   0x%06X %-20s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str)); n+=1
print("count:",n)
print()
print("=== raw dword scan of whole image for vtable base VA 0x00C98568 ===")
tv=0x400000+0x898568
for s in C.pe.sections:
    if s.SizeOfRawData==0: continue
    oo,_=C.off(s.VirtualAddress); raw=C.d[oo:oo+s.SizeOfRawData]
    for i in range(0,max(0,len(raw)-3)):
        v=struct.unpack_from("<I",raw,i)[0]
        if v==tv:
            print("   %s RVA 0x%X"%(s.Name.rstrip(b'\0').decode(errors='replace'),s.VirtualAddress+i))
