import pefile
from capstone import *
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
# disassemble 0x10003D00 .. 0x10003D80 (pipe name build before push \\.\Pipe\)
def dis(va_start, va_end):
    o=pe.get_offset_from_rva(va_start-ib)
    ln=va_end-va_start
    print("==== 0x%08X .. 0x%08X ===="%(va_start,va_end))
    for ins in md.disasm(d[o:o+ln], va_start):
        print("  %08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
dis(0x10003CA0, 0x10003D72)
