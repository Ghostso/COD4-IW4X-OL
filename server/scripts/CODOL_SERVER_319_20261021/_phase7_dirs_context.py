import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read()
for s,n in [(0xfc24,2252),(0x188f4,1746),(0x1f624,1796),(0x26da4,2645)]:
 print('\n',hex(s),n)
 print('before',d[s-64:s].hex())
 for i in range(3): print(i,[hex(x) for x in struct.unpack_from('<4I',d,s+16*i)])
