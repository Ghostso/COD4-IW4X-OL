import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
delta=0x30069e8d-0x23f5a4
for o in range(0x23fc00,0x240100):
 v=struct.unpack_from('<I',d,o)[0]
 if 0x30000000<=v<0x31000000:
  raw=v-delta
  print(hex(o),hex(v),'raw',hex(raw),'bytes',d[o:o+16].hex())
