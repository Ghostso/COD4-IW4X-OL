import struct,re,collections
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0x1f624;n=1796
rows=[]
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=28: continue
 b=d[off:off+sz]
 keys=[]
 for m in re.finditer(rb'SF_WEAPON_[A-Z0-9_]+_NAME',b): keys.append(m.group().decode())
 rows.append((i,off,sz,keys[:5]))
print('type28',len(rows),'with SF',sum(bool(r[3]) for r in rows))
for r in rows[:80]: print(r)
