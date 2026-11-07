import pefile
from capstone import *
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
def dis(va, n=60, before=0):
    rva=va-ib; o=pe.get_offset_from_rva(rva)
    print("---- VA 0x%08X (file 0x%06X) ----" % (va,o))
    i=0
    for ins in md.disasm(d[o:o+400], va):
        print("  %08X  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        i+=1
        if i>=n: break
for va in (0x10003D72, 0x10011B17, 0x10011C97, 0x10015AFE):
    dis(va)
