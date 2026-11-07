import pefile
from capstone import *
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
# OnRecvMsg 主体在 0x10015320 附近，cmd 分派 sub eax,1 / je 链在 0x100153B0 段
def dis(a,b,label=""):
    o=pe.get_offset_from_rva(a-ib)
    print("==== %s 0x%08X ===="%(label,a))
    n=0
    for ins in md.disasm(d[o:o+(b-a)], a):
        print("  %08X  %-24s %s %s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        n+=1
        if n>120: break
dis(0x100153B0, 0x100155A0, "OnRecvMsg cmd dispatch")
