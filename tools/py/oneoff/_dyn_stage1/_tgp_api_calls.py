from pathlib import Path
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=Path(r'WeGame/tgp_daemon.exe'); data=p.read_bytes(); pe=pefile.PE(data=data,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
want={'CreateProcessW','CreateProcessA','ShellExecuteExW','ShellExecuteW','GetCommandLineW','GetCommandLineA','CommandLineToArgvW','OpenFileMappingW','OpenFileMappingA','CreateFileMappingW','CreateFileMappingA','MapViewOfFile','CreateMutexW','CreateMutexA','OpenMutexW','OpenMutexA','CreateNamedPipeW','CreateNamedPipeA','ConnectNamedPipe','CreateFileW','CreateFileA','GetEnvironmentVariableW','GetEnvironmentVariableA','WinExec'}
iat={}
for ent in pe.DIRECTORY_ENTRY_IMPORT:
 for imp in ent.imports:
  if imp.name and imp.name.decode('latin1','replace') in want:
   iat[base+imp.address]=(ent.dll.decode('latin1'),imp.name.decode('latin1'))
print('TARGET IMPORTS',len(iat))
for k,v in sorted(iat.items()): print(hex(k),v)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
secs=[]
for s in pe.sections:
 if s.Characteristics & 0x20000000:
  secs.append((base+s.VirtualAddress,base+s.VirtualAddress+s.Misc_VirtualSize,s.Name.rstrip(b'\0').decode('latin1')))
def cstr(va,n=300):
 try:o=pe.get_offset_from_rva(va-base)
 except:return None
 if not 0<=o<len(data):return None
 e=data.find(b'\0',o,min(len(data),o+n)); e=e if e>=0 else min(len(data),o+n); b=data[o:e]
 if not b:return ''
 pr=sum(32<=x<127 or x in (9,10,13) for x in b)/len(b)
 return b.decode('latin1','replace') if pr>.82 else None
for start,end,sec in secs:
 code=data[pe.get_offset_from_rva(start-base):pe.get_offset_from_rva(end-base)]
 insns=list(md.disasm(code,start))
 for idx,ins in enumerate(insns):
  if ins.mnemonic!='call' or not ins.operands: continue
  op=ins.operands[0]
  if op.type!=2 or op.mem.base!=0 or op.mem.index!=0: continue
  va=op.mem.disp
  if va not in iat: continue
  print('\n'+'='*110); print('CALL',hex(ins.address),'->',iat[va], 'RVA',hex(ins.address-base))
  for j in range(max(0,idx-55),min(len(insns),idx+22)):
   x=insns[j]; mark='>>' if j==idx else '  '; ann=''
   for o in x.operands:
    if o.type==3:
     s=cstr(o.imm)
     if s is not None: ann+=' ; '+repr(s)
   print(f'{mark}{x.address-base:08X} {x.bytes.hex():<24} {x.mnemonic:<8} {x.op_str}{ann}')
