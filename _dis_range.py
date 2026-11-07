import struct
from pathlib import Path
from capstone import *
from capstone.x86 import *
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes(); base=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for start,end in ((0x364c0,0x36550),(0x36550,0x365e0),(0x365e0,0x36680),(0x36645,0x36720)):
 print('===',hex(start),hex(end),'===')
 for ins in md.disasm(D[start:end],base+start):
  print(f'{ins.address-base:08X} {ins.bytes.hex():<18} {ins.mnemonic:<8} {ins.op_str}')
