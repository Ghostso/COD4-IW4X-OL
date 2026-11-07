import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24; n=8557; A=0x28
# verify all type28 name pointer refs using 0x30000000 base mapping and print mismatches
ok=0; bad=0
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=28: continue
 b=d[A+off:A+off+sz]
 v=struct.unpack_from('<I',b,0)[0]
 if 0x30000000<=v<0x32000000:
  o=v-0x30000000
  if 0<=o<len(d):
   ok+=1
  else: bad+=1
print('type28 direct ptr-like',ok,'bad',bad)
