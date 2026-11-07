import struct,re,collections
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557
keys=collections.Counter()
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=28:continue
 b=d[off:off+sz]
 for x in re.findall(rb'SF_WEAPON_[A-Z0-9_]+',b): keys[x.decode()]+=1
print('unique',len(keys),'total',sum(keys.values()))
for k,v in keys.items():
 if 'M4' in k: print(k,v)
print('sample',list(keys)[:50])
