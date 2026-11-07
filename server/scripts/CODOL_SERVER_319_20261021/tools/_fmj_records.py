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
  # try every split into count chunks with 4-byte tags
  for recsz in range(8,40):
   if recsz*cnt!=len(pay): continue
   print('recsz',recsz)
   for j in range(cnt): print(j,pay[j*recsz:(j+1)*recsz].hex())
  print('tail strings',pay[32:])
