import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for i in range(30):
 o=0x23f983+i*20
 axis=d[o]; cnt=struct.unpack_from('<h',d,o+2)[0]; cont=struct.unpack_from('<i',d,o+4)[0]
 data=d[o+8:o+20]
 print(i,hex(o),'axis',axis,'cnt',cnt,'cont',hex(cont&0xffffffff),'data',data.hex())
