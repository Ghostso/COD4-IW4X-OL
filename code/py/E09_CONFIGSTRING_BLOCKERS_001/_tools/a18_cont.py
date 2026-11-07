import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== 0xA2660 continued, RVA 0xA2740..0xA28E0 (index/string/arrays) ===")
o,_=C.off(0xA2740); k=0
for ins in md.disasm(C.d[o:o+0x1B0], C.IB+0xA2740):
    print("   %06X %-18s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
    if k>=72: break
print()
print("=== strings near the index validators (VA 0xCB8334 group) ===")
for va in (0xCB8334,0xCB834C,0xCB835C,0xCB8378,0xCB83E0,0xCB83E8):
    b=C.bytes_rva(va-C.IB,80)
    print("   VA 0x%X : %r" % (va,(b.split(b'\0')[0] if b else None)))