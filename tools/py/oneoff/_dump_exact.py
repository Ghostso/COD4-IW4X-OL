import sys
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); md=Cs(CS_ARCH_X86,CS_MODE_32)
a=int(sys.argv[1],16); n=int(sys.argv[2],16); start=int(sys.argv[3],16)
b=D[a:a+n]
for x in md.disasm(b,0x400000+a):
 r=x.address-0x400000
 if r>start+n: break
 print(f"{r:08X} {x.bytes.hex():<20} {x.mnemonic:<10} {x.op_str}")

