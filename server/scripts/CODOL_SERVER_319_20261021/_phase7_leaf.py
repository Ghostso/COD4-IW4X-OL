import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
def leaf(o):
 fi,cc,bc,tc=struct.unpack_from('<HHii',d,o)
 mid=struct.unpack_from('<3f',d,o+12); half=struct.unpack_from('<3f',d,o+24); lbn=struct.unpack_from('<i',d,o+36)[0]
 return fi,cc,hex(bc&0xffffffff),tc,mid,half,lbn
for base in [0x23f984,0x23f997,0x23f9bf,0x23fe47]:
 print('\nbase',hex(base))
 for i in range(5):
  o=base+i*40
  if o+40<=len(d): print(i,hex(o),leaf(o))
