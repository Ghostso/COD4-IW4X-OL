import struct,re
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=43: continue
 b=d[off:off+sz]
 if b'fmj_shotgun' in b:
  print('idx',i,'off',hex(off),'size',hex(sz)); print(b.hex());
  for m in re.finditer(rb'[ -~]{3,}',b): print(hex(m.start()),m.group().decode())
  break
