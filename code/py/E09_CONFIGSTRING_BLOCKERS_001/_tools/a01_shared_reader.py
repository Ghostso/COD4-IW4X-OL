import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
def dis(rva,n,label):
    print("=== %s  RVA 0x%X ===" % (label,rva))
    o,nm=C.off(rva); k=0
    for ins in md.disasm(C.d[o:o+220], C.IB+rva):
        print("   %06X %-20s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=n: break
    print()
dis(0x1A07B0, 30, "shared reader entry (0x1A07B0) - callers call this")
dis(0x1A0660, 30, "callee 0x1A0660 (tag reader?)")
# jump table at RVA 0x1A086C
o,_=C.off(0x1A086C)
tbl=struct.unpack_from("<10I", C.d, o)
print("=== jump table @ RVA 0x1A086C (10 x u32, VA) ===")
for i,v in enumerate(tbl):
    print("   case %d -> VA 0x%X  (RVA 0x%X)" % (i,v,v-C.IB))