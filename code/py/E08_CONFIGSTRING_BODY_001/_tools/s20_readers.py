import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
def show(rva,n,label):
    print("=== %s RVA 0x%X ===" % (label,rva))
    o,_=S.off(rva); k=0
    for ins in md.disasm(S.d[o:o+120], S.IB+rva):
        print("   %06X %-18s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=n: break
    print()
# pairs where and,7 follows shr,3 within ~12 bytes
for rva in (0x5463A-0x14, 0x68343-0x20, 0x6A248-0x20, 0x6B162-0x18):
    show(rva, 22, "bit-read candidate")