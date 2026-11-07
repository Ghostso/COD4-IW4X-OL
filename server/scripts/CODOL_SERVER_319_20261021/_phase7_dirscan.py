import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read(); N=len(d)
def ok(o):
 t,off,ptr,size=struct.unpack_from('<4I',d,o)
 return t<100 and off<N and size<N and off+size<=N and ptr in (0,0xffffffff)
runs=[];o=0
while o+16<=N:
 if ok(o):
  s=o; rec=[]
  while o+16<=N and ok(o):
   rec.append(struct.unpack_from('<4I',d,o));o+=16
  if len(rec)>=3:runs.append((s,rec))
 else:o+=1
print('runs',len(runs))
for s,r in runs[:100]:
 print(hex(s),len(r),[(t,hex(off),hex(ptr),hex(sz)) for t,off,ptr,sz in r[:5]],'...',[(t,hex(off),hex(ptr),hex(sz)) for t,off,ptr,sz in r[-3:]])
