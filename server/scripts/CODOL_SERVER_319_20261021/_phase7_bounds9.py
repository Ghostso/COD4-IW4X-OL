import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for i in range(9):
 o=0x24008b+i*24
 print(i,hex(o),[round(x,3) for x in struct.unpack_from('<6f',d,o)])
