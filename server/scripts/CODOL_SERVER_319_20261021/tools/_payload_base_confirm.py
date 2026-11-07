import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24
for i in [2122,2123,2128,2129,2133,2134,2136,2138,2139,2228]:
    t,off,ptr,sz=struct.unpack_from('<4I',d,base+16*i)
    print(i,'raw',hex(off),'size',hex(sz),'bytes',d[off:off+32].hex())
