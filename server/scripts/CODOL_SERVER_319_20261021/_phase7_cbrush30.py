import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
s=0x23fc53
for i in range(30):
 o=s+i*36
 ns,g=struct.unpack_from('<HH',d,o); ptr=struct.unpack_from('<I',d,o+4)[0]
 print(i,hex(o),ns,g,hex(ptr),d[o:o+36].hex())
