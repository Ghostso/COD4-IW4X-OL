import struct
from pathlib import Path
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); pe=struct.unpack_from("<I",D,0x3c)[0]; n=struct.unpack_from("<H",D,pe+6)[0]; opt=pe+24; so=opt+struct.unpack_from("<H",D,pe+20)[0]; secs=[]
for i in range(n):
 h=so+40*i; nm=D[h:h+8].split(b"\0")[0].decode("latin1"); vs,va,rs,pr=struct.unpack_from("<IIII",D,h+8); secs.append((i,nm,va,vs,rs,pr))
T={0x3667a,0x36691}
for i,nm,va,vs,rs,pr in secs:
 if nm==".tvm0" or not rs: continue
 b=D[pr:pr+rs]
 for j in range(len(b)-5):
  a=va+j
  if b[j] in (0xe8,0xe9):
   t=a+5+struct.unpack_from("<i",b,j+1)[0]
   if t in T: print("rel32",hex(a),hex(t),hex(b[j]))
  if b[j]==0x0f and j+6<=len(b) and 0x80<=b[j+1]<=0x8f:
   t=a+6+struct.unpack_from("<i",b,j+2)[0]
   if t in T: print("jcc32",hex(a),hex(t),b[j:j+2].hex())
  if 0x70<=b[j]<=0x7f or b[j]==0xeb:
   t=a+2+struct.unpack_from("<b",b,j+1)[0]
   if t in T: print("rel8",hex(a),hex(t),hex(b[j]))

