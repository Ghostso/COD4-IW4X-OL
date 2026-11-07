import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\GDPOpenProtocol.tdr'
d=open(p,'rb').read()
def u32(o): return struct.unpack_from('<I',d,o)[0]
print('== header @0 ==')
print('magic2 0x%08x'%u32(0))
print('field0x20 %d (0x%x)'%(u32(8),u32(8)))
print('hash 0x%08x'%u32(12))
print('counts:',[u32(i) for i in (0x24,0x28,0x2c,0x30)])
print('== table region 0x94 ==')
print(d[0x94:0x94+256].hex(' '))
print(repr(d[0x94:0x94+256]))
# scan for the command name strings and record offsets
import re
names={}
for m in re.finditer(rb'GDP_[A-Z0-9_]{3,}',d):
    names.setdefault(m.group().decode(),[]).append(m.start())
print('\ntotal GDP_ names',len(names))
# print first 20 with offsets
for i,(k,v) in enumerate(sorted(names.items(), key=lambda kv: kv[1][0])[:25]):
    print('  %-52s %s'%(k,[hex(x) for x in v[:3]]))
