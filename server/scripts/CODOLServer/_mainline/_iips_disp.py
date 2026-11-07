import pefile
from capstone import *
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
o=pe.get_offset_from_rva(0x10015344-ib)
va=0x10015344
print("==== OnRecvMsg body (cmd dispatch) ====")
for ins in md.disasm(d[o:o+0x180], va):
    print("  %08X  %-22s %s %s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
