import struct
from pathlib import Path
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); ib=0x400000
for name,va in (("F8",0x1cd5ef8),("FC",0x1cd5efc),("ENTRY",0xe5dc690)):
 pat=struct.pack("<I",ib+va); pos=0; hits=[]
 while True:
  q=D.find(pat,pos)
  if q<0:break
  hits.append(q); pos=q+1
 print(name,hex(va),"VA hits",len(hits),[hex(x) for x in hits[:50]])
 pat=struct.pack("<I",va); pos=0; h2=[]
 while True:
  q=D.find(pat,pos)
  if q<0:break
  h2.append(q);pos=q+1
 print(name,hex(va),"RVA hits",len(h2),[hex(x) for x in h2[:50]])

