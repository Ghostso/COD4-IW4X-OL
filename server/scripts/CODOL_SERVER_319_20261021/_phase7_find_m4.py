import struct,re
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0x1f624; n=1796
for i in range(n):
    t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
    if t!=28: continue
    b=d[off:off+sz]
    keys=[x.decode() for x in re.findall(rb'SF_WEAPON_[A-Z0-9_]+_NAME',b) if b'M4' in x]
    if keys: print(i,hex(off),hex(sz),keys)
