import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for i in range(30):
 o=0x23f984+i*8
 ptr,c0,c1=struct.unpack_from('<Ihh',d,o)
 print(i,hex(o),hex(ptr),c0,c1)
