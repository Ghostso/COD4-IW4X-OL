import struct, math
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
allowed={0,0x08010000,0x080028c0,0x08033240,0x08030200}
for s in range(0x23f500,0x240500):
 ok=True; ptrs=0; nz=0
 for i in range(30):
  o=s+i*36
  ns=struct.unpack_from('<H',d,o)[0]
  ptr=struct.unpack_from('<I',d,o+4)[0]
  if not (ns==0 or 2<=ns<=64): ok=False;break
  if 0x30000000<=ptr<0x31000000: ptrs+=1
  elif ptr!=0: ok=False;break
 if not ok or ptrs<4: continue
 bo=s+30*36
 vals=[]
 for i in range(30):
  fs=struct.unpack_from('<6f',d,bo+i*24)
  if not all(math.isfinite(x) and abs(x)<1e5 for x in fs): ok=False;break
  vals.extend(fs)
 if not ok or not any(abs(v)>1e-5 for v in vals): continue
 co=bo+30*24
 cs=[struct.unpack_from('<I',d,co+i*4)[0] for i in range(30)]
 if all(x in allowed for x in cs): print('FOUND',hex(s),'ptrs',ptrs,'bounds',hex(bo),'contents',hex(co),'flags',[hex(x) for x in cs])
