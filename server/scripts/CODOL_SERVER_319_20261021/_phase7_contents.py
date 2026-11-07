import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for i in range(9): print(i,hex(0x240163+i*4),hex(struct.unpack_from('<I',d,0x240163+i*4)[0]),d[0x240163+i*4:0x240163+i*4+4].hex())
print('after',d[0x240187:0x240220].hex())
