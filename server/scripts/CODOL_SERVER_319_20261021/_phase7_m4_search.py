import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); b=d[0x22c3666:0x22c3666+0x11a2]
for val in [1/300,1/500,0.003333,0.003,0.002,0.05,0.1,0.95,1.0,30.0,33.0,100.0]:
 print(val,[hex(o) for o in range(0,len(b)-4) if abs(struct.unpack_from('<f',b,o)[0]-val)<1e-7][:40])
