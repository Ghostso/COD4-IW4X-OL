import pefile
from capstone import *
p=r"COD OL\IIPS\iips.dll"
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
    n=0
    for ins in md.disasm(d[o:o+(b-a)], a):
        extra=""
        if "dword ptr [0x" in ins.op_str:
            try:
                tgt=int(ins.op_str.split("[")[1].split("]")[0],16); n2=nm(tgt)
                if n2: extra="  ; "+n2
            except: pass
        print("  %08X  %-22s %s %s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, extra))
        n+=1
        if n>80: break
dis(0x10015280, 0x10015420, "OnRecvMsg cmd dispatch")
