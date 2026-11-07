import pefile
from capstone import *
p=r"COD OL\IIPS\IIPSHost.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
def dis(a,b,label="",lim=80):
    o=pe.get_offset_from_rva(a-ib)
    print("==== %s 0x%08X ===="%(label,a))
    n=0
    for ins in md.disasm(d[o:o+(b-a)], a):
        print("  %08X  %-22s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
        n+=1
        if n>lim: break
dis(0x10010710, 0x10010800, "MD5 final + hex format")
