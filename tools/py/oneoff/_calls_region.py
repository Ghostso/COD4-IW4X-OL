import struct
from pathlib import Path
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); pe=struct.unpack_from("<I",D,0x3c)[0]; n=struct.unpack_from("<H",D,pe+6)[0]; opt=pe+24; so=opt+struct.unpack_from("<H",D,pe+20)[0]; secs=[]
for i in range(n):
 h=so+40*i; nm=D[h:h+8].split(b"\0")[0].decode("latin1"); vs,va,rs,pr=struct.unpack_from("<IIII",D,h+8); secs.append((i,nm,va,vs,rs,pr))
for i,nm,va,vs,rs,pr in secs:
 if nm==".tvm0" or not rs: continue
 b=D[pr:pr+rs]
 for j in range(len(b)-5):
  if b[j]!=0xe8: continue
  a=va+j; t=a+5+struct.unpack_from("<i",b,j+1)[0]
  if 0x36600<=t<0x36a00: print(hex(a),hex(t))

