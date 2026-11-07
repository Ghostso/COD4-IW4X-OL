import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557;A=0x28
names={'fmj_base','highcal_base','flashhider_base','scope_none','akimbo_base','silencer_m4','heartbeat_base','quickdraw_base','eotech_base','gl_acr'}
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=43:continue
 b=d[A+off:A+off+sz]
 if len(b)<12:continue
 nr,cnt,er=struct.unpack_from('<III',b,0)
 if nr!=0xffffffff:continue
 e=b.find(b'\0',12)
 if e<0:continue
 nm=b[12:e].decode('latin1','replace')
 if nm not in names:continue
 pay=b[e+1:]
 print('\n',nm,'count',cnt,'pay',len(pay))
 for j in range(cnt):
  r=pay[j*12:(j+1)*12]
  if len(r)<12:break
  print(j,r.hex(),'b0=%02x b1=%02x u16=%04x off=%08x val=%08x'%(r[0],r[1],struct.unpack_from('<H',r,2)[0],struct.unpack_from('<I',r,4)[0],struct.unpack_from('<I',r,8)[0]))
