import struct,math
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read(); allowed={0,0x08010000,0x080028c0,0x08033240,0x08030200}
for s in [0x23fc53,0x23fc57,0x23fc9f,0x23ff47,0x23ff4b]:
 print('start',hex(s))
 for n in [9,30]:
  bo=s+n*36
  ok=True; vals=[]
  for i in range(n):
   fs=struct.unpack_from('<6f',d,bo+i*24)
   if not all(math.isfinite(x) and abs(x)<1e5 for x in fs): ok=False;break
   vals+=fs
  co=bo+n*24
  cs=[struct.unpack_from('<I',d,co+i*4)[0] for i in range(n)] if ok else []
  print(' n',n,'bounds',hex(bo),'finite',ok,'nz',sum(abs(x)>1e-5 for x in vals),'contents', [hex(x) for x in cs[:12]],'good',sum(x in allowed for x in cs))
