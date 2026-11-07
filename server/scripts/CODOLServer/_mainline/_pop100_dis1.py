import pefile
from capstone import *
p=r"COD OL\codoMP_client_shipRetail.exe"
b=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
# VA = fileoff + 0x714000  => fileoff = VA - 0x714000
def dis(va, before=0x80, after=0x90):
    off = va - 0x714000
    start = off - before
    print("==== VA 0x%08X (file 0x%06X) ====" % (va, off))
    base = va - before
    n=0
    for ins in md.disasm(b[start:off+after], base):
        mark = "  <<<" if ins.address==va else ""
        print("  %08X  %-22s %s %s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
        n+=1
        if n>60: break
dis(0x008444DA)
print()
dis(0x008844A2)
