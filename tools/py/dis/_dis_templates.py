from pathlib import Path
from capstone import *
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes(); base=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for a,b in ((0x36670,0x36700),(0xaa176,0xaa250),(0xb2d90,0xb2e30)):
 print('===',hex(a),hex(b),'===')
 for i in md.disasm(D[a:b],base+a):
  print(f'{i.address-base:08X} {i.bytes.hex():<18} {i.mnemonic:<8} {i.op_str}')
