import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); b=d[0x22c3666:0x22c3666+0x11a2]
for shift in [0,0x330]:
 print('shift',hex(shift))
 print([round(struct.unpack_from('<f',b,0xa4c+shift+4*i)[0],3) for i in range(20)])
