import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\GDPOpenProtocol.tdr'
d=open(p,'rb').read()
print('size',len(d))
print('head 128:',d[:128].hex(' '))
print('tail 64 :',d[-64:].hex(' '))
# string table region: find where ascii strings start
import re
first=None
for m in re.finditer(rb'[\x20-\x7e]{6,}',d):
    first=m.start(); break
print('first string at',hex(first))
# count structure: u32 dwords before strings
print('dwords 0..64:',[hex(struct.unpack_from('<I',d,i)[0]) for i in range(0,64,4)])
# entropy-ish: how much is non-ascii
import collections
c=collections.Counter(d[:first])
print('header byte histogram top:',c.most_common(10))
