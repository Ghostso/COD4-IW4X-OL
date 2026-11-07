import pefile
from capstone import *
p=r"COD OL\IIPS\iips_policymsg.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        if f.name: iat[f.address]=f.name.decode()
def nm(a): return iat.get(a,"")
def dis(a,b,label=""):
    o=pe.get_offset_from_rva(a-ib)
    print("==== %s 0x%08X ===="%(label,a))
    for ins in md.disasm(d[o:o+(b-a)], a):
        extra=""
        if "dword ptr [0x" in ins.op_str:
            try:
                tgt=int(ins.op_str.split("[")[1].split("]")[0],16); n2=nm(tgt)
                if n2: extra="  ; "+n2
            except: pass
        if ins.mnemonic in ("call",) and ins.op_str.startswith("0x"):
            extra += "  ; call %s"%ins.op_str
        print("  %08X  %-22s %s %s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, extra))
dis(0x10001060, 0x100011D0, "policy crypto init (key + taes_setkey)")
