from pathlib import Path
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=Path(r'COD OL/TCLS/Client.exe'); d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
print('BASE',hex(base))
for s in pe.sections: print(s.Name.rstrip(b'\0'), 'VA',hex(s.VirtualAddress),'VS',hex(s.Misc_VirtualSize),'RAW',hex(s.PointerToRawData),'RS',hex(s.SizeOfRawData))
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
for ent in pe.DIRECTORY_ENTRY_IMPORT:
 for imp in ent.imports:
  if imp.name and imp.name in (b'CreateProcessW',b'ShellExecuteExW',b'CreateFileW',b'GetCommandLineA'):
   print('IMP',ent.dll,imp.name,'IAT_VA',hex(imp.address),'IAT_RVA',hex(imp.address-base),'IAT_FILE',hex(pe.get_offset_from_rva(imp.address-base)))
# call site raw offsets from direct byte search
for name,raw in [('CreateProcessW',0x2228e),('ShellExecuteExW',0x222da)]:
 rva=pe.get_rva_from_offset(raw); va=base+rva
 print('\nRAW',name,hex(raw),'RVA',hex(rva),'VA',hex(va))
 lo=va-0x180; o1=pe.get_offset_from_rva(lo-base); o2=pe.get_offset_from_rva(va+0x40-base)
 md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
 for ins in md.disasm(d[o1:o2],lo):
  mark='>>' if ins.address==va else '  '
  print(mark,hex(ins.address-base),ins.bytes.hex(),ins.mnemonic,ins.op_str)
