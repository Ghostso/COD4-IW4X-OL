# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
out=[]
out.append("=== OpenSSL object-method dispatch pattern: mov ecx,[r+8]; mov eax,[ecx+0x1c]; jmp eax ===")
insns=list(sweep(md,text,base))
for i,ins in enumerate(insns):
    if ins.mnemonic=="mov" and ins.op_str.startswith("ecx, dword ptr [") and "+ 8]" in ins.op_str:
        w=insns[i:i+4]
        if len(w)>=3 and w[1].mnemonic=="mov" and "+ 0x1c]" in w[1].op_str and w[2].mnemonic=="jmp":
            out.append("   dispatch at 0x%06X : %s | %s | %s"%(ins.address-C.IB,ins.op_str,w[1].op_str,w[2].op_str))
out.append("")
out.append("=== all call sites to 0x672460 ===")
for ins in insns:
    if ins.mnemonic=="call" and ins.op_str.startswith("0x"):
        if int(ins.op_str,16)-C.IB==0x672460:
            out.append("   0x%06X"%(ins.address-C.IB))
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_data\out_sslmethods.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
