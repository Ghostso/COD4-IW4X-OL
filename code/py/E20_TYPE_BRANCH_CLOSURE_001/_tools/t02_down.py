import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_tools")
from pe_helper import PE
from capstone import *
p=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=PE(p)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
out=[]
def show(a,b,tag):
    out.append("="*74); out.append("%s RVA 0x%X..0x%X"%(tag,a,b)); out.append("-"*74)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
        r=ins.address-C.IB; m=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==1: m=" -> RVA 0x%X"%((op.imm-C.IB)&0xffffffff)
        out.append("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
    out.append("")
show(0x6A84E0,0x6A8600,"0xAA84E0 (payload alloc/ctor)")
show(0x6A9720,0x6A9820,"0xAA9720 (2nd object ctor)")
show(0x6A9260,0x6A9300,"0xAA9260 (post-proc)")
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_data\out_downstream.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
