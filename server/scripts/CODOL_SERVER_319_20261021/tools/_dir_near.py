import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24
for i in range(2226,2233):
 print(i,[hex(x) for x in struct.unpack_from('<4I',d,base+i*16)])
