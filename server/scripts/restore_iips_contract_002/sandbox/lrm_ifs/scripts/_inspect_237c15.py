import pathlib,struct
from capstone import *
D=pathlib.Path('codoMP_client_shipRetail.exe').read_bytes()
# section #0 raw 0x1000 VA 0x1000
base=0x1000; raw=0x1000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for va in (0x237B80,0x237C00,0x237C15,0x237C25):
 o=raw+va-base
 print('\n--',hex(va),'file',hex(o),'bytes',D[o:o+32].hex())
 for ins in md.disasm(D[o:o+64],0x400000+va):
  print('%08X  %-20s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic+' '+ins.op_str))
  if ins.address>=0x400000+va+24: break
