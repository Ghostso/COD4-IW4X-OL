import sys,pefile
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001\_tools")
from pe_helper import PE
from capstone import *
p=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=PE(p)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
pe=pefile.PE(p,fast_load=False)
mp={}
for e in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[]):
    for imp in e.imports:
        nm=imp.name.decode(errors="replace") if imp.name else "ord_%d"%imp.ordinal
        mp[imp.address]=(e.dll.decode(errors="replace"),nm)
out=[]
def show(a,b,tag):
    out.append("="*74); out.append("%s RVA 0x%X..0x%X"%(tag,a,b)); out.append("-"*74)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
        r=ins.address-C.IB; m=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
                elif op.type==2 and op.mem.disp in mp:
                    dll,nm=mp[op.mem.disp]; m=" -> %s!%s"%(dll,nm)
        out.append("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
    out.append("")
show(0x6ABBC0,0x6ABF00,"0x6ABBC0")
show(0x788100,0x7881A0,"0x788133 site")
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001\_data\out_6abbc0.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
