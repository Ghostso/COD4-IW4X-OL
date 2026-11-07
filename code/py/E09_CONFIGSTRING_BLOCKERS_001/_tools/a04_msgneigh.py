import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== client Msg module neighborhood: RVA 0x1AC000 .. 0x1AD200 ===")
print("known: 0x1AC1D0 = MSG_ReadData (byte copy)")
o,_=C.off(0x1AC000)
k=0
for ins in md.disasm(C.d[o:o+0x1200], C.IB+0x1AC000):
    rva=ins.address-C.IB
    # print prologues and any that look like bit ops
    if ins.mnemonic=="push" and ins.op_str=="ebp":
        print("  --- prologue @ RVA 0x%X ---" % rva)
    k+=1
print("total insns in window:",k)