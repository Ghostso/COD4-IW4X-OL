import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== error string referenced by case 3/4: VA 0xCB4568 -> RVA 0x%X ===" % (0xCB4568-C.IB))
b=C.bytes_rva(0xCB4568-C.IB, 120)
print("   %r" % (b.split(b'\0')[0] if b else None))
print()
print("=== VA 0xCB6CB8 (used by 0x1A0660) / 0xCB5D58 ===")
for va in (0xCB6CB8,0xCB5D58):
    b=C.bytes_rva(va-C.IB,120)
    print("   VA 0x%X -> %r" % (va,(b.split(b'\0')[0] if b else None)))
print()
# resolve the dispatcher targets
for rva,label in ((0x633FE0,"case 0,1,5,6,7 -> 0x633FE0"),(0x6340E0,"case 8 -> 0x6340E0"),(0xB50850,"case 8 -> 0xB50850")):
    print("=== %s  RVA 0x%X ===" % (label,rva))
    o,_=C.off(rva); k=0
    for ins in md.disasm(C.d[o:o+70], C.IB+rva):
        print("   %06X %-18s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=10: break
    print()