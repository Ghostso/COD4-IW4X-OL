import pefile
from capstone import *
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
def dis(a,b):
    o=pe.get_offset_from_rva(a-ib)
    print("==== 0x%08X ===="%a)
    for ins in md.disasm(d[o:o+(b-a)], a):
        print("  %08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
# function called at 0x10003CD0 -> 0x10005130: likely builds pipe name / reads HostPid
dis(0x10005130, 0x10005290)
