import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== format string @ VA 0xCB8334 -> RVA 0x%X ===" % (0xCB8334-C.IB))
b=C.bytes_rva(0xCB8334-C.IB,140)
print("   %r" % (b.split(b'\0')[0] if b else None))
print()
def dis(rva,n,lab):
    print("=== %s  RVA 0x%X ===" % (lab,rva))
    o,_=C.off(rva); k=0
    for ins in md.disasm(C.d[o:o+0x300], C.IB+rva):
        print("   %06X %-18s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=n: break
    print()
dis(0xA2660, 66, "candidate 0xA2660")