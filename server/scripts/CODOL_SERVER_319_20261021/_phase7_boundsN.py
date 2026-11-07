import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for i in range(20):
 o=0x24008b+i*24
 fs=struct.unpack_from('<6f',d,o)
 allf=all(abs(x)<1e5 and x==x for x in fs)
 print(i,hex(o),allf,[round(x,3) for x in fs])
