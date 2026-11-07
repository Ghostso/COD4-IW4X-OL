import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557; ASSET_BASE=0x28
print('zone',hex(len(d)))
for i in range(n-5,n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 print(i,hex(t),hex(off),hex(sz),'end_raw',hex(off+sz),'end_base',hex(ASSET_BASE+off+sz))
print('last entries')
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t==43:
  print('first43',i,hex(off),hex(sz), 'actualhead',d[ASSET_BASE+off:ASSET_BASE+off+32].hex())
  e=d.find(b'\xff\xff\xff\xff',ASSET_BASE+off,ASSET_BASE+off+sz)
  cnt=struct.unpack_from('<I',d,e+4)[0]
  print('meta',hex(e-(ASSET_BASE+off)),cnt)
  break
