from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_MEM
fn=r'COD OL\TCLS\Client.exe'
pe=pefile.PE(fn,fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
iat={}
for e in pe.DIRECTORY_ENTRY_IMPORT:
 d=e.dll.decode(errors='replace')
 for imp in e.imports:
  if imp.name: iat[imp.address]=(d,imp.name.decode(errors='replace'))
want={'CreateProcessW','GetCommandLineA','CreateFileW','ShellExecuteExW'}
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for sec in pe.sections:
 if not (sec.Characteristics & 0x20000000): continue
 blob=sec.get_data(); va=pe.OPTIONAL_HEADER.ImageBase+sec.VirtualAddress
 for ins in md.disasm(blob,va):
  for op in ins.operands:
   if op.type==CS_OP_MEM and op.mem.base==0 and op.mem.index==0 and op.mem.disp in iat and iat[op.mem.disp][1] in want:
    print(hex(ins.address),iat[op.mem.disp],ins.mnemonic,ins.op_str)
