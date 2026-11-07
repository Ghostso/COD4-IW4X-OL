import struct
from pathlib import Path
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); ib=0x400000; T={ib+0x1cd5ef8,ib+0x1cd5efc}
bases=[(0x1000,0x593000),(0x8a8000,0x16e000),(0xa16000,0x62000),(0xe5c8000,0x1000),(0xe5c9000,0xa000),(0xe5d7000,0x6000)]
for va,rs in bases:
 b=D[va:va+rs]
 for t in T:
  pat=struct.pack("<I",t); pos=0
  while True:
   q=b.find(pat,pos)
   if q<0:break
   print(hex(t-ib),hex(va+q),b[max(0,q-8):q+12].hex())
   pos=q+1

