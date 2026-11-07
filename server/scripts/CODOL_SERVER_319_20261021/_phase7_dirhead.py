import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for o in range(0x1180,0x11e0,4): print(hex(o),hex(struct.unpack_from('<I',d,o)[0]))
print('first recs')
for i in range(5):
 o=0x11c1+16*i; print(i,hex(o),[hex(x) for x in struct.unpack_from('<4I',d,o)])
print('last recs')
for i in range(186,191):
 o=0x11c1+16*i; print(i,hex(o),[hex(x) for x in struct.unpack_from('<4I',d,o)])
