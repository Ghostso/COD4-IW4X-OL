import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for a,b,tag in [(0x1FA680,0x1FA700,"ref 0x1FA6BF"),(0x2C38F0,0x2C3960,"ref 0x2C3922")]:
    print("="*72); print("%s 0x%X..0x%X"%(tag,a,b)); print("-"*72)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
        r=ins.address-C.IB; m=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
        print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
    print()
