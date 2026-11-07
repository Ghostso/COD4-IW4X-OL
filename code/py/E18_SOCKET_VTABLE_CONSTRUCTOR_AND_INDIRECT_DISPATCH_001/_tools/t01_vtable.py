# -*- coding: utf-8 -*-
import sys,struct,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
IB=C.IB
def read_slots(rva,n):
    o,_=C.off(rva)
    return [(rva+i*4, struct.unpack_from("<I",C.d,o+i*4)[0]) for i in range(n)]
print("=== vtable candidate: scan 0x898540..0x898700 ===")
o,_=C.off(0x898540)
for i in range(0,0x1C0,4):
    rva=0x898540+i
    v=struct.unpack_from("<I",C.d,o+i)[0]
    tag=""
    if v>=IB and v<IB+0xD958000: tag=" RVA 0x%X"%((v-IB)&0xffffffff)
    elif 0xB0000<=v<0xD0000: tag=" (VA out of .text?)"
    print("   0x%06X: 0x%08X%s"%(rva,v,tag))
