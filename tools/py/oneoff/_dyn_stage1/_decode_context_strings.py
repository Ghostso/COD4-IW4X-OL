from pathlib import Path
import pefile
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
for fn in ['client_launcher.exe','tgp_daemon.exe','Client.exe']:
 path=(ROOT/'WeGame'/fn) if fn!='Client.exe' else (ROOT/'COD OL'/'TCLS'/fn)
 data=path.read_bytes(); pe=pefile.PE(data=data,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
 print('\n###',path)
 for va in [0x432794,0x4327a0,0x432930,0x4329b0,0x432a0c,0x432a24,0x432b10,0x445b7a,0x445b8c,0x445ba6,0x4c9b24,0x4cbf68,0x4cc35c,0x4cc368,0x4cc394,0x4cc3a4]:
  try:o=pe.get_offset_from_rva(va-base)
  except:continue
  if 0<=o<len(data):
   # utf16-le decode to NUL
   e=o
   while e+1<len(data) and data[e:e+2]!=b'\0\0': e+=2
   try: s=data[o:e].decode('utf-16-le')
   except: s='<decode>'
   print(hex(va),repr(s),'ascii',repr(data[o:o+80].split(b'\0',1)[0]))
