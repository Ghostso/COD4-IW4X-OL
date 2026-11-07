import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557;A=0x28
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=43: continue
 b=d[A+off:A+off+sz]; nr,cnt,er=struct.unpack_from('<III',b,0)
 if nr!=0xffffffff: continue
 e=b.find(b'\0',12); nm=b[12:e].decode('latin1','replace') if e>=0 else ''
 if nm=='fmj_base':
  pay=b[e+1:]
  print('len',len(pay),'hex',pay.hex())
  for o in range(len(pay)-3):
   v=struct.unpack_from('<I',pay,o)[0]
   if v in (0x0e78,0x0d14,0x0d04,0x0e6c,0x0e54,0x0d28,0x0d2c,0x0d30,0x0d34,0x0d38,0x0d3c,0x0da8,0x0e6c): print('offset candidate',o,hex(v))
