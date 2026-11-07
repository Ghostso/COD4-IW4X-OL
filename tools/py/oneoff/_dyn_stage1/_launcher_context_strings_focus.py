from pathlib import Path
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
files=[ROOT/'WeGame'/'client_launcher.exe',ROOT/'COD OL'/'TCLS'/'Client.exe',ROOT/'WeGame'/'tgp_daemon.exe']
for path in files:
 data=path.read_bytes(); pe=pefile.PE(data=data,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
 # map VA to file offset
 def foff(va):
  try:return pe.get_offset_from_rva(va-base)
  except:return None
 def show(va):
  o=foff(va)
  if o is None or o>=len(data): return None
  e=data.find(b'\0',o,min(len(data),o+400))
  if e<0:return None
  b=data[o:e]
  if not b:return ''
  ok=sum(32<=x<127 or x in (9,10,13) for x in b)
  return b.decode('latin1','replace') if ok/len(b)>.75 else None
 print('\n###',path.name)
 # all ASCII runs >=4 from relevant sections
 for sec in pe.sections:
  if not (sec.Characteristics & 0x40000000): continue
  raw=sec.get_data(); rva=sec.VirtualAddress; import re
  for m in re.finditer(rb'[\x20-\x7e]{4,}',raw):
   s=m.group().decode('latin1')
   if any(k.lower() in s.lower() for k in ['launcher','startfor','game_id','client.exe','tcls','codomp','session','context','platform','account','ticket','token','auth','pipe','instance','environment','commandline','parent','gamepath','game_path']):
    print(f'RVA={rva+m.start():#x} VA={base+rva+m.start():#x} {s!r}')
