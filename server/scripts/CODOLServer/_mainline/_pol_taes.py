import pefile
from capstone import *
p=r"COD OL\IIPS\iips_policymsg.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
def dis(a,b,label=""):
    o=pe.get_offset_from_rva(a-ib)
    print("==== %s 0x%08X ===="%(label,a))
    for ins in md.disasm(d[o:o+(b-a)], a):
        print("  %08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
# taes_setkey
dis(0x100061C0, 0x10006280, "taes_setkey")
# the send function: 0x10001520
dis(0x10001520, 0x10001640, "policy send/setup")
