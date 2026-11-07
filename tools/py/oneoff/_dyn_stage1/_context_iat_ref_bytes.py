from pathlib import Path
import pefile,struct,re
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
for rel,vas in [
 ('WeGame/tgp_daemon.exe',[0x4c6084,0x4c6088,0x4c608c,0x4c6090,0x4c6094,0x4c60a0,0x4c60a8,0x4c6114,0x4ca68c,0x4c9b24,0x4cbc14,0x4cbf68]),
 ('WeGame/client_launcher.exe',[0x43201c,0x432020,0x432024,0x432000,0x432004,0x432150,0x432158,0x432930,0x4329b0]),
 ('COD OL/TCLS/Client.exe',[0x41f004,0x41f024,0x41f124,0x41f13c]),
]:
 path=ROOT/rel; data=path.read_bytes(); pe=pefile.PE(data=data,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
 print('\n###',rel)
 for va in vas:
  pat=struct.pack('<I',va); hits=[]; st=0
  while True:
   i=data.find(pat,st)
   if i<0:break
   try:r=pe.get_rva_from_offset(i)
   except:r=None
   hits.append((i,r))
   st=i+1
  print(hex(va),[(hex(o),hex(r) if r is not None else None) for o,r in hits[:40]],'count',len(hits))
