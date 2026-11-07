import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557
wanted={'m4':'SF_WEAPON_M4A1TECH_MP_NAME','ak':'SF_WEAPON_AK47_MP_NAME','r870':'SF_WEAPON_R870_MP_NAME','mp5':'SF_WEAPON_MP5K_MP_NAME'}
blobs={}
for k,w in wanted.items():
 for i in range(n):
  t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
  if t!=28:continue
  b=d[off:off+sz]
  if w.encode() in b: blobs[k]=b;break
for o in range(0xd20,0xd80,4):
 print(hex(o),[(k,struct.unpack_from('<i',b,o)[0],round(struct.unpack_from('<f',b,o)[0],5)) for k,b in blobs.items()])
