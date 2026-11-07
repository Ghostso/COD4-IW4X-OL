from pathlib import Path
import pefile,struct
from capstone import *
from capstone.x86 import *
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\WeGame\client_launcher.exe')
data=ROOT.read_bytes(); pe=pefile.PE(data=data,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
allins=[]; secs=[]
for s in pe.sections:
 if s.Characteristics & 0x20000000:
  st=base+s.VirtualAddress; raw=s.get_data(); ins=list(md.disasm(raw,st)); allins+=ins; secs.append((st,st+len(raw),s.Name.rstrip(b'\0').decode()))
def cstr(va,n=400):
 try:o=pe.get_offset_from_rva(va-base)
 except:return None
 if not 0<=o<len(data): return None
 e=data.find(b'\0',o,min(len(data),o+n))
 if e<0:return None
 b=data[o:e]
 if not b:return ''
 ok=sum(32<=x<127 or x in (9,10,13) for x in b)
 return b.decode('latin1','replace') if ok/len(b)>.75 else None
for target in [0x409265,0x40973a,0x40969d,0x4015b9,0x4094,0x4094b]:
 print('\nTARGET',hex(target))
 for i,ins in enumerate(allins):
  if ins.mnemonic=='call' and ins.operands:
   op=ins.operands[0]
   if op.type==X86_OP_IMM and op.imm==target:
    print('CALLSITE',hex(ins.address),'RVA',hex(ins.address-base))
    for z in allins[max(0,i-25):min(len(allins),i+8)]:
     ann=''
     for o in z.operands:
      if o.type==X86_OP_IMM:
       s=cstr(o.imm)
       if s is not None:ann+=' ; '+repr(s)
     print(f'{"=>" if z.address==ins.address else "  "}{z.address-base:08X} {z.bytes.hex():<20} {z.mnemonic:<8} {z.op_str}{ann}')
