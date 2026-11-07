import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for i in range(9):
 o=0x240090+i*24
 mid=struct.unpack_from('<3f',d,o); half=struct.unpack_from('<3f',d,o+12)
 print(i,hex(o),'mid',tuple(round(x,3) for x in mid),'half',tuple(round(x,3) for x in half))
for i in range(9): print('contents',i,hex(struct.unpack_from('<I',d,0x240168+i*4)[0]))
