import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for o in range(0,0x100,4): print('%04x %08x'%(o,struct.unpack_from('<I',d,o)[0]))
