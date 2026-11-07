import pefile
from capstone import *
p=r"COD OL\ace-ats32.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
e=pe.DIRECTORY_ENTRY_EXPORT
print("=== ace-ats32.dll exports @ ImageBase 0x%X ==="%ib)
for s in e.symbols:
    print("   ord %-3s VA 0x%08X  %s"%(s.ordinal, ib+s.address, s.name.decode() if s.name else ""))
print()
for s in e.symbols:
    va = ib + s.address
    off = pe.get_offset_from_rva(s.address)
    print("---- %s @ VA 0x%08X ----"%(s.name.decode() if s.name else "ord%s"%s.ordinal, va))
    n=0
    for ins in md.disasm(d[off:off+0x70], va):
        print("   %08X  %-20s %s %s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        n+=1
        if n>18: break
