# -*- coding: utf-8 -*-
import sys, struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
tables=[]
for ins in sweep(md,text,base):
    if ins.mnemonic=="jmp" and ins.op_str.startswith("dword ptr [") and "*4 + 0x" in ins.op_str:
        try:
            disp=int(ins.op_str.split("*4 + 0x")[1].split("]")[0],16)
        except Exception:
            continue
        tables.append((ins.address-C.IB,disp))
print("jump tables found:",len(tables))
for site,disp in tables:
    # disp is a VA displacement (absolute)
    rva=disp-C.IB
    if not (0<=rva<0x10000000): 
        print("  0x%06X -> 0x%X (outside image)"%(site,disp)); continue
    oo,_=C.off(rva)
    if oo is None:
        print("  0x%06X -> 0x%X (no raw)"%(site,disp)); continue
    entries=[]
    for i in range(12):
        v=struct.unpack_from("<I",C.d,oo+i*4)[0]
        if not (C.IB<=v<C.IB+0x10000000): break
        entries.append(v-C.IB)
    print("  site 0x%06X table 0x%X entries=%s"%(site,disp,["0x%X"%e for e in entries]))
