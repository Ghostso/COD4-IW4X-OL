import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read()
for o in range(0xfbc0,0xfc40,4): print(hex(o),hex(struct.unpack_from('<I',d,o)[0]))
print('tail around table end')
for o in range(0x312b0,0x31380,4): print(hex(o),hex(struct.unpack_from('<I',d,o)[0]))
print('last entries')
for i in range(8540,8557):
 o=0xfc24+16*i; print(i,hex(o),[hex(x) for x in struct.unpack_from('<4I',d,o)])
