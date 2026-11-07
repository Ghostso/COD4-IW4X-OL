import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
def dis(rva,n,label):
    print("=== %s RVA 0x%X ===" % (label,rva))
    o,_=C.off(rva); k=0
    for ins in md.disasm(C.d[o:o+180], C.IB+rva):
        print("   %06X %-20s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=n: break
    print()
# scan the Msg module for the MSB-first read-bit shape: 'mov cl, byte [esi+0x10]' ; and ax, 1 ; ...
for rva in (0x1AC070,0x1AC120,0x1AC190,0x1AC2B0):
    dis(rva, 26, "candidate")