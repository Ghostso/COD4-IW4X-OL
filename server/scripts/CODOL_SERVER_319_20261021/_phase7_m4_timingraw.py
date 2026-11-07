import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); b=d[0x22c3666:0x22c3666+0x11a2]
for o in range(0x550,0x620,4):
 print('%03x i=%9d f=%12.6g'%(o,struct.unpack_from('<i',b,o)[0],struct.unpack_from('<f',b,o)[0]))
