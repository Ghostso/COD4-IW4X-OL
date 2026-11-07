# -*- coding: utf-8 -*-
import sys,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print("=== libcurl version/strings ===")
for pat in [rb"libcurl/[0-9.]+", rb"7\.38\.0", rb"curl_easy", rb"Easy", rb"multi"]:
    print("  %r count=%d"%(pat,len(re.findall(pat,C.d))))
print()
print("=== 0xA84CE0 (delivery point) ===")
o,_=C.off(0xA84CE0)
for ins in md.disasm(C.d[o:o+0xB0],C.IB+0xA84CE0):
    r=ins.address-C.IB; m=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
    print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
