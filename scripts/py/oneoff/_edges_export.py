import struct
from pathlib import Path
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes(); ib=0x400000
pe=struct.unpack_from('<I',D,0x3c)[0]; n=struct.unpack_from('<H',D,pe+6)[0]; opt=pe+24; so=opt+struct.unpack_from('<H',D,pe+20)[0]
secs=[]
for i in range(n):
 h=so+40*i; nm=D[h:h+8].split(b'\0')[0].decode('latin1'); vs,va,rs,pr=struct.unpack_from('<IIII',D,h+8); secs.append((i,nm,va,vs,rs,pr))
print('edges with source in 0x36400..0x36800')
for i,nm,va,vs,rs,pr in secs:
 if nm=='.tvm0' or not rs: continue
 b=D[pr:pr+rs]
 for j in range(len(b)-6):
  a=va+j
  if not (0x36400<=a<0x36800): continue
  if b[j] in (0xe8,0xe9):
   t=a+5+struct.unpack_from('<i',b,j+1)[0]; print('rel',hex(a),hex(b[j]),'->',hex(t))
  elif b[j]==0x0f and 0x80<=b[j+1]<=0x8f:
   t=a+6+struct.unpack_from('<i',b,j+2)[0]; print('jcc',hex(a),'->',hex(t))
print('abs refs to named exports')
for val,lab in ((0x364f0,'364f0'),(0x36510,'36510'),(0x36520,'36520'),(0x36570,'36570'),(0x365e0,'365e0')):
 pat=struct.pack('<I',ib+val); pos=0; out=[]
 while True:
  q=D.find(pat,pos)
  if q<0: break
  out.append(q);pos=q+1
 if out: print(lab,[hex(x) for x in out])
