from pathlib import Path
import pefile,re,struct
from capstone import *
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
p=root/r"COD OL\WeGameLauncher\launcher.exe"
d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
print("base",hex(base),"entry",hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
terms=[b"StartFor",b"AddPath",b"tgp_daemon.exe",b"game_id",b"launcher_ver",b"TCLS",b"TCLS_SHAREDMEMEMORY",b"cmd_start_for.ini",b"cmd_launcher_info.ini",b"codoMP_client_shipRetail.exe"]
for t in terms:
 offs=[];q=0
 while True:
  i=d.find(t,q)
  if i<0:break
  offs.append(i);q=i+1
 print("TERM",t,"offs",[hex(x) for x in offs])
 for o in offs:
  try: av=base+pe.get_rva_from_offset(o)
  except:continue
  print(" STR",hex(av))
  q=0
  while True:
   i=d.find(struct.pack("<I",av),q)
   if i<0:break
   try: x=base+pe.get_rva_from_offset(i)
   except:q=i+1;continue
   print("  REF",hex(x))
   q=i+1
