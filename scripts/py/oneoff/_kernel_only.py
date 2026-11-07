import struct
from pathlib import Path
from capstone import *
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); IB=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
starts=(0x36675,0x36680,0x36689,0x36691,0x36697,0x3669c)
for st in starts:
 print("===",hex(st),"===")
 for x in md.disasm(D[st:st+48],IB+st):
  print(f"{x.address-IB:08X} {x.bytes.hex():<18} {x.mnemonic:<8} {x.op_str}")
