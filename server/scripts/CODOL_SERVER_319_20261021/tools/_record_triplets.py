import struct
from collections import Counter
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557;A=0x28
c=Counter()
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=43:continue
 b=d[A+off:A+off+sz]
 if len(b)<12:continue
 nr,cnt,er=struct.unpack_from('<III',b,0)
 if nr!=0xffffffff:continue
 e=b.find(b'\0',12)
 if e<0:continue
 pay=b[e+1:]
 pre=b[e+1:]
 for j in range(cnt):
  r=pay[j*12:(j+1)*12]
  if len(r)<12:break
  c[(r[0],r[1],struct.unpack_from('<H',r,2)[0])]+=1
print('triplets',len(c))
for k,v in c.most_common(80): print(k,v)
