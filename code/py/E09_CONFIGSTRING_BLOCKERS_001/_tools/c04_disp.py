import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== callers of the configstring consumer 0xA2660 (dispatcher candidates) ===")
import struct
# gather disasm of 0x3512A0 and 0x352E80 (the 3 call sites' functions)
for rva,n in ((0x3512A0,46),(0x352E80,60)):
    print("--- func 0x%X ---" % rva)
    o,_=C.off(rva); k=0
    for ins in md.disasm(C.d[o:o+0x260], C.IB+rva):
        print("   %06X %-16s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=n: break
    print()