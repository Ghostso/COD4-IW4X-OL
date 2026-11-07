import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); off=0x19c266c
print(d[off:off+0x120].hex())
print(''.join(chr(x) if 32<=x<127 else '.' for x in d[off:off+0x120]))
