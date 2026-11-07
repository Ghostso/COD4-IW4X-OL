# -*- coding: utf-8 -*-
import sys, struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print("client ImageBase",hex(C.IB))
print("server ImageBase",hex(S.IB))
def str_at(P,va,n=64):
    rva=va-P.IB
    b=P.bytes_rva(rva,n)
    return rva,(b.split(b"\0")[0] if b else None)
# server references used in WriteGamestate
for va in (0x7C0B90,0x7C0A00,0x7C0A05):
    print("server str VA 0x%X ->"%va, str_at(S,va))
# client: strings we care about (same VA space, recovered image)
for va in (0xCB8378,0xCB8334,0xCB8344,0xCB834C,0xCB8354,0xCB835C,0xCB3894,0xCB7770,0xCD6384,0xCB6C78,0xCD6328,0xCA204A):
    print("client str VA 0x%X ->"%va, str_at(C,va,80))
