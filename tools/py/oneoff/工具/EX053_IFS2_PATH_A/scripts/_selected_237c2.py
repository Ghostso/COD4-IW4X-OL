import pathlib
from capstone import *
D=pathlib.Path('codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
for va in [0x237C25,0x237C2B,0x237C31,0x237C33,0x237C3E,0x237C43,0x237C4D,0x237C60,0x237C80]:
 print('\nSTART',hex(va))
 for ins in md.disasm(D[va:va+48],IB+va):
  print('%08X %-16s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic+' '+ins.op_str))
  if ins.address>=IB+va+32:break


