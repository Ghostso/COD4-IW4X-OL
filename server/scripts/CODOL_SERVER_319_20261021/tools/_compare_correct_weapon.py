import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557; A=0x28
# compare known weapon fields under corrected slicing against alpha ref offsets b68/e? and previous
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=28: continue
 b=d[A+off:A+off+sz]
 if b'SF_WEAPON_M4A1TECH_MP_NAME' in b:
  print('m4 idx',i,'off',hex(off),'size',hex(sz),'actual',hex(A+off))
  for o in [0x55c,0x574,0x590,0x5c8,0x670,0x674,0x778,0x780,0x784,0x794,0x7a4,0x884,0x890,0x898,0x950,0x954,0x9a0,0xd38,0xd3c,0xd40,0xd44,0xd50,0xd58,0xd74,0xe90,0xe98,0xb68,0xb60]:
   if o+4<=len(b): print(hex(o),hex(struct.unpack_from('<I',b,o)[0]),struct.unpack_from('<i',b,o)[0],round(struct.unpack_from('<f',b,o)[0],4))
  break
