import pefile, struct
from capstone import *
from capstone.x86 import *

def imports(path):
 pe=pefile.PE(path,fast_load=True);pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']]);d={}
 for e in pe.DIRECTORY_ENTRY_IMPORT:
  for i in e.imports:d[i.address]=e.dll.decode('latin1')+'!'+((i.name or b'').decode('latin1') if i.name else '#'+str(i.ordinal))
 return pe,d
def dis(path,lo,hi):
 pe,imp=imports(path);s=next(x for x in pe.sections if x.Name.rstrip(b'\0')==b'.text');base=pe.OPTIONAL_HEADER.ImageBase+s.VirtualAddress;md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
 print('###',path,hex(lo),hex(hi))
 for ins in md.disasm(s.get_data()[lo-base:hi-base],lo):
  n=''
  if ins.mnemonic in ('call','jmp') and ins.operands:
   o=ins.operands[0]
   if o.type==X86_OP_IMM:n=' -> '+hex(o.imm)
   elif o.type==X86_OP_MEM and o.mem.base==0 and o.mem.index==0:n=' IMP '+imp.get(o.mem.disp,'UNK@'+hex(o.mem.disp))
  print(f'{ins.address:08X}: {ins.bytes.hex():<24} {ins.mnemonic:<8} {ins.op_str}{n}')

dis(r'WeGame\client_launcher.exe',0x409200,0x409480)
dis(r'WeGame\client_launcher.exe',0x40f5a0,0x40f850)
