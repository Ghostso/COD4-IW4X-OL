import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557
# print exact directory record for index and nearby records
for i in range(3706,3712):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+16*i)
 print(i,hex(t),hex(off),hex(ptr),hex(sz))
# type43 first few
print('43')
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+16*i)
 if t==43:
  print(i,hex(off),hex(sz),hex(off+sz),d[off:off+48].hex()); break
