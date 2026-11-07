import pefile
from capstone import *
p=r"COD OL\IIPS\IIPSHost.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        nm=f.name.decode() if f.name else "ord"
        iat[f.address]=nm
def dis(a,b,label=""):
    o=pe.get_offset_from_rva(a-ib)
    print("==== %s 0x%08X ===="%(label,a))
    n=0
    for ins in md.disasm(d[o:o+(b-a)], a):
        extra=""
        if "dword ptr [0x" in ins.op_str:
            try:
                tgt=int(ins.op_str.split("[")[1].split("]")[0],16)
                if tgt in iat: extra="  ; "+iat[tgt]
            except: pass
        print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,extra))
        n+=1
        if n>95: break
dis(0x1000DAE0, 0x1000DC80, "CreateNamedPipeA call")
