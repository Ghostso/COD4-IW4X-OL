import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== 0xA2660 tail: RVA 0xA282C..0xA2930 (A3 count + 0xA2480 per-record) ===")
o,_=C.off(0xA282C); k=0
for ins in md.disasm(C.d[o:o+0x104], C.IB+0xA282C):
    print("   %06X %-18s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
    if k>=70: break