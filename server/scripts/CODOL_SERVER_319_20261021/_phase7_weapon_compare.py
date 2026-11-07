import struct,re
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557
names=['SF_WEAPON_AK47_MP_NAME','SF_WEAPON_R870_MP_NAME','SF_WEAPON_RPG_MP_NAME','SF_WEAPON_M4A1TECH_MP_NAME']
for want in names:
 for i in range(n):
  t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
  if t!=28:continue
  b=d[off:off+sz]
  if want.encode() in b:
   print('\n',want,i,hex(off),hex(sz))
   for o in [0x860,0x884,0x890,0x898,0x8a0,0x8a4,0x8c8,0x8cc,0xe90,0xe94,0xe98,0xe9c,0xea0]:
    print(hex(o),struct.unpack_from('<i',b,o)[0],hex(struct.unpack_from('<I',b,o)[0]))
   break
 else: print('not found',want)
