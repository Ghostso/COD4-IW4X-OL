import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
delta=0x30069e8d-0x23f5a4
s0=0x23f81c; s1=0x23f8f4
hits=[]
for o in range(len(d)-4):
 v=struct.unpack_from('<I',d,o)[0]
 if 0x30000000<=v<0x31000000:
  raw=v-delta
  if s0<=raw<s1:
   hits.append((o,v,raw,(raw-s0)//8))
print('hits',len(hits))
for i,(o,v,raw,idx) in enumerate(hits):
 print(i,hex(o),hex(v),'side',idx,'next+', (hits[i+1][0]-o if i+1<len(hits) else 0),'bytes',d[o-8:o+44].hex())
