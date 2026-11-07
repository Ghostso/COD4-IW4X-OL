import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
def dis(rva,n,label):
    print("=== %s  RVA 0x%X ===" % (label,rva))
    o,_=C.off(rva); k=0
    for ins in md.disasm(C.d[o:o+160], C.IB+rva):
        print("   %06X %-18s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=n: break
    print()
dis(0x1A0808, 16, "case default/0 (0x1A0808)")
dis(0x1A0817, 14, "case 9 (0x1A0817)")
dis(0x1A083D, 12, "case 8 (0x1A083D)")
dis(0x1A0853, 16, "case 3/4 (0x1A0853)")