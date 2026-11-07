import struct
from collections import Counter
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24; n=8557; A=0x28
B0=Counter(); B1=Counter(); U=Counter(); D=Counter(); E=Counter(); rows=[]
for i in range(n):
    t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
    if t!=43: continue
    b=d[A+off:A+off+sz]
    if len(b)<12: continue
    nr,cnt,er=struct.unpack_from('<III',b,0)
    if nr!=0xffffffff: continue
    e=b.find(b'\0',12)
    if e<0: continue
    nm=b[12:e].decode('latin1','replace'); pay=b[e+1:]
    for j in range(cnt):
        r=pay[j*12:(j+1)*12]
        if len(r)<12: break
        B0[r[0]]+=1; B1[r[1]]+=1; U[struct.unpack_from('<H',r,2)[0]]+=1
        D[struct.unpack_from('<I',r,4)[0]]+=1; E[struct.unpack_from('<I',r,8)[0]]+=1
        rows.append((nm,j,r))
print('b0',B0.most_common(30)); print('b1',B1.most_common(30)); print('u16',U.most_common(30)); print('D',D.most_common(30)); print('E',E.most_common(20)); print('total',len(rows))
