import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557
for i in [2129,2133,2134,2136,2138,2139,2228]:
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16); b=d[off:off+sz]
 pos=b.find(b'\xff\xff\xff\xff'); count=struct.unpack_from('<I',b,pos+4)[0]; e=b.find(b'\0',pos+12)
 print(i,hex(off),'size',sz,'meta',hex(pos),'count',count,'nameend',hex(e),'afterlen',sz-(e+1),'after',b[e+1:].hex())
