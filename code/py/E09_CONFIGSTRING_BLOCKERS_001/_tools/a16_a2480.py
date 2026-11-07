import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
def dis(rva,n,lab):
    print("=== %s  RVA 0x%X ===" % (lab,rva))
    o,_=C.off(rva); k=0
    for ins in md.disasm(C.d[o:o+0x400], C.IB+rva):
        print("   %06X %-18s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=n: break
    print()
dis(0xA2480, 70, "candidate 0xA2480")