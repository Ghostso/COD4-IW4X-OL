import struct, collections, os
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); N=len(d)
def ok(o):
 if o+16>N:return False
 t,off,ptr,sz=struct.unpack_from('<4I',d,o)
 return t<64 and off<N and sz<N and off+sz<=N and ptr in (0,0xffffffff)
runs=[];o=0
while o+16<=N:
 if ok(o):
  s=o; rec=[]
  while o+16<=N and ok(o):
   rec.append(struct.unpack_from('<4I',d,o));o+=16
  if len(rec)>=20:runs.append((s,rec))
 else:o+=1
print('runs',len(runs))
for s,r in sorted(runs,key=lambda x:-len(x[1]))[:10]:
 print(hex(s),len(r),collections.Counter(x[0] for x in r),'first',r[:3],'last',r[-3:])
