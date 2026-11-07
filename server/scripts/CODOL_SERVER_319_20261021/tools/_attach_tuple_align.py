import struct,json
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557;A=0x28
names={'fmj_base','highcal_base','flashhider_base','scope_none','akimbo_base','silencer_m4','heartbeat_base'}
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=43: continue
 b=d[A+off:A+off+sz]
 name_ref,count,ent_ref=struct.unpack_from('<III',b,0)
 if name_ref!=0xffffffff: continue
 e=b.find(b'\0',12)
 if e<0: continue
 nm=b[12:e].decode('latin1','replace')
 if nm not in names: continue
 pay=b[e+1:]
 print('\n',nm,'count',count,'payload',len(pay),pay.hex())
 for shift in range(0,min(12,len(pay))):
  if shift+12*count>len(pay): continue
  rows=[struct.unpack_from('<3I',pay,shift+12*j) for j in range(count)]
  if all(r[1] < 64 for r in rows): print(' shift',shift,rows)
