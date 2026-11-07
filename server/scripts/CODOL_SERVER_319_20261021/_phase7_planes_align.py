import struct,math
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for o in range(0x23f5a0,0x23f5ac):
 n=struct.unpack_from('<3f',d,o); dist=struct.unpack_from('<f',d,o+12)[0]; l2=sum(x*x for x in n)
 print(hex(o),n,dist,l2)
