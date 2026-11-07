import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24;n=8557
for i in [2122,2123,2128,2129,2130,2131,2133,2134,2136,2138,2139]:
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 print('\nidx',i,'off',hex(off),'size',hex(sz),'before',d[off-16:off].hex(),'head',d[off:off+24].hex())
