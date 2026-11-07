import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for i in range(20):
 o=0x23fc53+i*36
 v=struct.unpack_from('<I',d,o+4)[0]
 print(i,hex(o),'num/glass',struct.unpack_from('<HH',d,o),'sides',hex(v),'tail',d[o+8:o+36].hex())
