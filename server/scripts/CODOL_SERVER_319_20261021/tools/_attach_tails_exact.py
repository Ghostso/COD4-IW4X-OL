import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557
names={'fmj_base','highcal_base','flashhider_base','scope_none','akimbo_base','heartbeat_base','silencer_m4'}
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=43: continue
 b=d[off:off+sz]
 # find metadata triple
 pos=-1
 for j in range(0,max(0,len(b)-11)):
  if b[j:j+4]==b'\xff'*4 and struct.unpack_from('<I',b,j+4)[0]<=64 and b[j+8:j+12]==b'\xff'*4:
   e=b.find(b'\0',j+12)
   if e>=0:
    nm=b[j+12:e].decode('latin1','replace')
    if nm in names: pos=j; name=nm; cnt=struct.unpack_from('<I',b,j+4)[0]; end=e+1; break
 if pos>=0:
  print('\n',name,'idx',i,'raw',hex(off),'size',hex(sz),'meta',hex(pos),'count',cnt)
  print('prefix',b[:end].hex())
  print('tail',b[end:].hex())
