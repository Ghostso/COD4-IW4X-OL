from pathlib import Path
import pefile,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=Path(r'COD OL/TCLS/Client.exe'); d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
iat={}
for ent in pe.DIRECTORY_ENTRY_IMPORT:
 for imp in ent.imports:
  if imp.name: iat[imp.address]=ent.dll.decode()+ '!' + imp.name.decode()
text=[s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text'][0]
start=base+text.VirtualAddress; end=start+text.Misc_VirtualSize; off=text.PointerToRawData; raw=d[off:off+text.SizeOfRawData]
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
ins=list(md.disasm(raw,start))
for idx,x in enumerate(ins):
 if x.mnemonic!='call' or not x.operands: continue
 op=x.operands[0]
 if op.type==2 and op.mem.base==0 and op.mem.index==0 and op.mem.disp in iat:
  print('\n'+'='*100);print('CALL',hex(x.address),hex(x.address-base),'->',iat[op.mem.disp])
  for y in ins[max(0,idx-45):idx+20]:
   mark='>>' if y.address==x.address else '  '
   print(mark,hex(y.address-base),y.bytes.hex(),y.mnemonic,y.op_str)
