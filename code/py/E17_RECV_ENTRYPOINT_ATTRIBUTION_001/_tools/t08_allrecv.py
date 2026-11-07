# -*- coding: utf-8 -*-
import sys,pefile
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
p=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=PE(p)
pe=pefile.PE(p,fast_load=False)
mp={}
for e in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[]):
    for imp in e.imports:
        nm=imp.name.decode(errors="replace") if imp.name else "ord_%d"%imp.ordinal
        mp[imp.address]=(e.dll.decode(errors="replace"),nm)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
want={"0xbae490":"recv","0xbae50c":"recvfrom","0xbae4e0":"__WSAFDIsSet","0xbae504":"sendto","0xbae4c8":"send"}
rows=[]
for ins in sweep(md,text,base):
    for op in ins.operands:
        if op.type==X86_OP_MEM and op.mem.disp in (0xBAE490,0xBAE50C,0xBAE504,0xBAE4C8):
            dll,nm=mp[op.mem.disp]
            rows.append((ins.address-C.IB, nm, ins.mnemonic, ins.op_str))
from collections import Counter
print("=== all recv/recvfrom/send/sendto call sites ===")
for t,n in Counter(r[1] for r in rows).most_common(): print("  %s: %d"%(t,n))
print()
for r,nm,m,op in sorted(rows,key=lambda x:(x[1],x[0])):
    print("  0x%06X %-10s %s %s"%(r,nm,m,op))
