import struct,math
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for s in range(0x23fc40,0x23fc60):
 bo=s+30*36; co=bo+30*24
 ok=all(math.isfinite(x) and abs(x)<1e5 for i in range(30) for x in struct.unpack_from('<6f',d,bo+i*24))
 cs=[struct.unpack_from('<I',d,co+i*4)[0] for i in range(30)]
 print(hex(s),hex(bo),ok,sum(x in {0,0x08010000,0x080028c0,0x08033240,0x08030200} for x in cs),hex(cs[0]),hex(cs[-1]))
