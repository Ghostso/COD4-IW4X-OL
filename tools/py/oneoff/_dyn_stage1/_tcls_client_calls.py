from pathlib import Path
import pefile, struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=Path(r'COD OL/TCLS/Client.exe'); data=p.read_bytes(); pe=pefile.PE(data=data,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sites=[0x42228E,0x4222DA]
secs=[(base+s.VirtualAddress,base+s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData),s.Name.rstrip(b'\0').decode('latin1')) for s in pe.sections]
def cstr(va,n=240):
 try:o=pe.get_offset_from_rva(va-base)
 except:return None
 if not 0<=o<len(data):return None
 e=data.find(b'\0',o,min(len(data),o+n)); e=e if e>=0 else min(len(data),o+n); b=data[o:e]
 if not b:return ''
 pr=sum(32<=x<127 or x in (9,10,13) for x in b)/len(b)
 return b.decode('latin1','replace') if pr>.8 else None
for site in sites:
 print('\n'+'='*100); print('CALL',hex(site))
 for lo,hi in [(site-0x400,site+0x80)]:
  o1=pe.get_offset_from_rva(lo-base); o2=pe.get_offset_from_rva(hi-base)
  for ins in md.disasm(data[o1:o2],lo):
   mark='>>' if ins.address==site else '  '; ann=''
   if ins.mnemonic.startswith('push') and ins.operands and ins.operands[0].type==3:
    s=cstr(ins.operands[0].imm)
    if s is not None:ann=' ; '+repr(s)
   print(f'{mark}{ins.address-base:08X} {ins.bytes.hex():<20} {ins.mnemonic:<8} {ins.op_str}{ann}')
