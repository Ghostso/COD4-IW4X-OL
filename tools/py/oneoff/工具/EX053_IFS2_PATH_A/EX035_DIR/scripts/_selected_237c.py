import pathlib
from capstone import *
D=pathlib.Path('codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
for va in [0x237BF0,0x237BFF,0x237C01,0x237C09,0x237C0D,0x237C15,0x237C1B]:
 print('\nSTART',hex(va))
 for ins in md.disasm(D[va:va+48],IB+va):
  print('%08X %-16s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic+' '+ins.op_str))
  if ins.address>=IB+va+32:break

