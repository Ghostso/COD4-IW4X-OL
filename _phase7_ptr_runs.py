import struct
road=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021'
for path in [road+r'\_map_extract\coop_train_zone.bin', road+r'\_map_extract\mp_firingrange_zone.bin']:
 d=open(path,'rb').read(); runs=[]; o=0
 while o+8<=len(d):
  a,b=struct.unpack_from('<II',d,o)
  if 0x30000000<=a<0x31000000 and b==0:
   s=o; arr=[]
   while o+8<=len(d):
    a,b=struct.unpack_from('<II',d,o)
    if not (0x30000000<=a<0x31000000 and b==0): break
    arr.append(a); o+=8
   if len(arr)>=3: runs.append((s,len(arr),arr))
  else: o+=4
 print('\n',path,'runs',len(runs))
 for s,n,a in runs:
  ds=[a[i+1]-a[i] for i in range(n-1)]
  from collections import Counter
  c=Counter(ds).most_common(3)
  print(f'{s:08x} n={n:<4} first={a[0]:08x} last={a[-1]:08x} ds={c}')
