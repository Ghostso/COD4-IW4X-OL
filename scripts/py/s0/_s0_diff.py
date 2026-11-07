import sys
from capstone import *
A=sys.argv[1]; B=sys.argv[2]
a=open(A,"rb").read(); b=open(B,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
def dis(buf, off, va, n=24):
    for i in md.disasm(buf[off:off+64], va):
        print("    %08X  %-20s %s %s"%(i.address, i.bytes.hex(), i.mnemonic, i.op_str))
        n-=1
        if n<=0: break
print("=== BASELINE .text @RVA0x1000 (VA 0x10001000) ===")
dis(a,0x1000,0x10001000)
print("=== IN-USE .text @RVA0x1000 ===")
dis(b,0x1000,0x10001000)
print()
print("=== BASELINE .rdata @RVA0x33000 as dwords ===")
import struct
for k in range(0,0x70,4):
    print("    0x%05X: %08X"%(0x33000+k, struct.unpack_from("<I", a, 0x33000+k)[0]))
print("=== IN-USE .rdata @RVA0x33000 as bytes ===")
print("   ", b[0x33000:0x33070])
print("=== BASELINE .data @RVA0x42000 as string refs ===")
seg=a[0x42000:0x42420]
import re
for m in re.finditer(rb"[\x20-\x7e]{4,}", seg):
    print("    +0x%03X %r"%(m.start(), m.group()))
