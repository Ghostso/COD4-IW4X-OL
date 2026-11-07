import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read()
for v in [0x317c1ead,0x317c1eb8,0x317d9c51,0x317c1f41,0x317d9ca1,0x317c2507]:
    print(hex(v),'low',hex(v&0xffffff),'hi',hex(v>>24))
    for base in [0x30000000,0x31000000,0x30069e8d]:
        o=(v&0xffffff)+(base-0x30000000)
        if 0<=o<len(d): print(' base',hex(base),'o',hex(o),'ascii',d[o:o+48])
