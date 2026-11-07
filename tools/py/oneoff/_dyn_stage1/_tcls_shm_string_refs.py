from pathlib import Path
import pefile,struct,re
from capstone import *
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
rel=r"WeGame\tcls\tcls_core.exe";p=root/rel;d=p.read_bytes();pe=pefile.PE(data=d);base=pe.OPTIONAL_HEADER.ImageBase
vas=[0x55924c,0x55934c,0x5648b0,0x5822e8]
for va in vas:
 print("=== STR",hex(va))
 # refs to VA (4-byte absolute), and refs to RVA to catch relative offsets
 for val,typ in [(va,"VA"),(va-base,"RVA")]:
  hits=[];q=0;pat=struct.pack("<I",val)
  while True:
   i=d.find(pat,q)
   if i<0:break
   try: hits.append(base+pe.get_rva_from_offset(i))
   except:pass
   q=i+1
  print(typ,[hex(x) for x in hits])
 # dump bytes around string UTF16 decoding
 off=pe.get_offset_from_rva(va-base)
 x=d[off:off+160]
 print("STRBYTES",x[:100])
