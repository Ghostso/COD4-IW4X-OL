import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print("=== 0x06D5D0: candidate outer dispatcher (calls MSG_ReadBits + A3-record reader 0xA2480) ===")
o,_=C.off(0x6D5D0); k=0
for ins in md.disasm(C.d[o:o+0x260], C.IB+0x6D5D0):
    m=""
    if ins.mnemonic=="call":
        for op in ins.operands:
            if op.type==X86_OP_IMM: m=" -> 0x%X"%(op.imm-C.IB)
    print("   %06X %-16s %s%s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str,m)); k+=1
    if k>=66: break