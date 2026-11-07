# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print("=== server strings ===")
for va in (0x7C4E20,0x7C4E23,0x7C4E28,0x7C0B90,0x7C0A0E):
    b=S.bytes_rva(va-S.IB,48)
    print("  0x%X %r"%(va,b.split(b"\0")[0] if b else None))
print()
out=[]
def show(P,a,b,tag):
    out.append("="*74); out.append("%s  0x%X..0x%X"%(tag,a,b)); out.append("-"*74)
    o,_=P.off(a)
    for ins in md.disasm(P.d[o:o+(b-a)],P.IB+a):
        r=ins.address-P.IB; m=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==1: m=" -> 0x%X"%((op.imm-P.IB)&0xffffffff)
        out.append("  %06X %-24s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
    out.append("")
show(C,0x3512A0,0x351400,"CLIENT 0x3512A0 from entry (part1)")
show(C,0x350040,0x350170,"CLIENT 0x350040 (opcode1 handler)")
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_data\out_3512a0_entry.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
