import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
def ok(o):
 ptr,c0,c1=struct.unpack_from('<Ihh',d,o)
 return 0x30000000<=ptr<0x31000000 and -1<=c0<=10000 and -1<=c1<=10000
runs=[]; o=0
while o+8<=len(d):
 if ok(o):
  s=o; rec=[]
  while o+8<=len(d) and ok(o):
   rec.append(struct.unpack_from('<Ihh',d,o)); o+=8
  if len(rec)>=2: runs.append((s,rec))
 else:o+=1
print('runs',len(runs))
for s,rec in runs[:100]:
 print(hex(s),len(rec),[(hex(a),b,c) for a,b,c in rec[:5]],'...',[(hex(a),b,c) for a,b,c in rec[-3:]])
