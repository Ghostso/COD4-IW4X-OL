import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for s in range(0x240088,0x2400a0):
 vals=struct.unpack_from('<6f',d,s)
 if all(abs(x)<100000 and x==x for x in vals): print(hex(s),[round(x,3) for x in vals])
