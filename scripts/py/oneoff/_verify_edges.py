import struct
from pathlib import Path
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes(); ib=0x400000
pe=struct.unpack_from('<I',D,0x3c)[0]; n=struct.unpack_from('<H',D,pe+6)[0]; opt=pe+24; so=opt+struct.unpack_from('<H',D,pe+20)[0]
secs=[]
for i in range(n):
 h=so+40*i; nm=D[h:h+8].split(b'\0')[0].decode('latin1'); vs,va,rs,pr=struct.unpack_from('<IIII',D,h+8); ch=struct.unpack_from('<I',D,h+36)[0]; secs.append((i,nm,va,vs,rs,pr,ch))
hits=[]
for i,nm,va,vs,rs,pr,ch in secs:
 if nm=='.tvm0' or not rs: continue
 b=D[pr:pr+rs]
 for j in range(len(b)-6):
  b0=b[j]
  if b0 in (0xe8,0xe9):
   t=va+j+5+struct.unpack_from('<i',b,j+1)[0]
   if 0x365a0 <= t < 0x367e0: hits.append((va+j,b0,t,'rel'))
  if b0==0x0f and 0x80<=b[j+1]<=0x8f:
   t=va+j+6+struct.unpack_from('<i',b,j+2)[0]
   if 0x365a0 <= t < 0x367e0: hits.append((va+j,(b[j]<<8)|b[j+1],t,'jcc'))
print('CTRL NEAR 365A0-367E0',len(hits))
for a,op,t,kind in hits: print(hex(a),hex(op),'->',hex(t),kind)
for t in (0x365e0,0x36675,0x3667a,0x36680,0x36691,0x36697,0x36790):
 for val,lab in ((ib+t,'VA'),(t,'RVA')):
  pat=struct.pack('<I',val); pos=0; out=[]
  while True:
   q=D.find(pat,pos)
   if q<0:break
   out.append(q);pos=q+1
  if out: print('PTR',hex(t),lab,[hex(x) for x in out[:30]])
