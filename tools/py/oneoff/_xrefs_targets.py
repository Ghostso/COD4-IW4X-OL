import struct
from pathlib import Path
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); ib=0x400000
T={0x36675,0x3667a,0x36680,0x36691,0x36697,0x366dc,0x365e0,0x36790}
for i,nm,va,rs,pr,ch in [(0,".tp3",0x1000,0x593000,0x1000,0x60000020),(1,".tp3",0x8a8000,0x16e000,0x594000,0x40000040),(2,".tp3",0xa16000,0x62000,0x702000,0xc0000040),(3,".tp3",0xe5c8000,0x1000,0x764000,0xc0000040),(4,".tp3",0xe5c9000,0xa000,0x765000,0x40000040),(6,".tp3",0xe5d7000,0x6000,0x771000,0xe0000020)]:
 b=D[pr:pr+rs]
 for j in range(len(b)):
  a=va+j
  # rel32 direct call/jcc
  if j+6<=len(b) and (b[j] in (0xe8,0xe9) or (b[j]==0x0f and 0x80<=b[j+1]<=0x8f)):
   sz=5 if b[j] in (0xe8,0xe9) else 6; off=1 if sz==5 else 2
   t=a+sz+struct.unpack_from("<i",b,j+off)[0]
   if t in T: print("rel32",hex(a),hex(t),b[j:j+sz].hex())
  if j+2<=len(b) and (0x70<=b[j]<=0x7f or b[j]==0xeb):
   t=a+2+struct.unpack_from("<b",b,j+1)[0]
   if t in T: print("rel8",hex(a),hex(t),b[j:j+2].hex())
 # ptrs
 for t in T:
  for pat,kind in ((struct.pack("<I",t),"RVA"),(struct.pack("<I",ib+t),"VA")):
   q=0
   while True:
    q=b.find(pat,q)
    if q<0:break
    print("ptr",kind,hex(va+q),hex(t));q+=1

