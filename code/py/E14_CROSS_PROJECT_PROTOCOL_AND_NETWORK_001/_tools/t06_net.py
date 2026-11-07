# -*- coding: utf-8 -*-
import sys,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for va in (0xC37244,0xCB3AF8,0xCB2854,0xCA204A):
    b=C.bytes_rva(va-C.IB,96)
    print("  0x%X %r"%(va,b.split(b"\0")[0] if b else None))
print()
print("=== 0x672460 ===")
o,_=C.off(0x672460)
for ins in md.disasm(C.d[o:o+0x70],C.IB+0x672460):
    r=ins.address-C.IB; m=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
    print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
print()
pats=[b"SSL_",b"mbedtls",b"OpenSSL",b"EVP_",b"BIO_"]
hits={}
for s in C.pe.sections:
    if s.SizeOfRawData==0: continue
    o2,_=C.off(s.VirtualAddress); raw=C.d[o2:o2+s.SizeOfRawData]
    for p in pats:
        c=len(list(re.finditer(re.escape(p),raw)))
        if c: hits[p]=hits.get(p,0)+c
print("crypto/ssl string counts:",{k.decode():v for k,v in hits.items()})
