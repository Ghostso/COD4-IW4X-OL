from pathlib import Path
from capstone import *
D=Path('codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
for a,b in ((0x364f0,0x366b0),(0xaa12a,0xaa1a0),(0xb2d70,0xb2dc0),(0x485380,0x4853d0)):
 print('\n=== %X..%X ==='%(a,b))
 f=0x1000+(a-0x1000)
 for x in md.disasm(D[f:f+(b-a)],IB+a): print('%08X %-22s %s %s'%(x.address-IB,x.bytes.hex(),x.mnemonic,x.op_str))
