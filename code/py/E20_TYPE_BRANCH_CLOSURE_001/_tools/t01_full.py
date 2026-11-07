import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_tools")
from pe_helper import PE
from capstone import *
p=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=PE(p)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
out=[]
o,_=C.off(0x6A9920)
for ins in md.disasm(C.d[o:o+0x260],C.IB+0x6A9920):
    r=ins.address-C.IB; m=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==1: m=" -> RVA 0x%X"%((op.imm-C.IB)&0xffffffff)
    out.append("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_data\out_6a9920_full.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
