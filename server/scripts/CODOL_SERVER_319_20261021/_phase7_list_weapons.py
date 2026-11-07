import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read()
base=0x1f624; n=1796
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t==28:
  b=d[off:off+sz]; pos=0xBFC
  if pos<len(b):
   e=b.find(b'\0',pos); name=b[pos:e].decode('latin1') if e>=0 else '?'
  else:name='?'
  print(i,hex(off),hex(sz),repr(name),b[:16].hex())
