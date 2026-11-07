import struct
from pathlib import Path
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes()
for t in (0x1cd5ef4,0x1cd5ef8,0x1cd5efc):
 print('GLOBAL',hex(t))
 pat=struct.pack('<I',t); pos=0
 while True:
  q=D.find(pat,pos)
  if q<0:break
  print(hex(q),D[q-16:q+20].hex(' '))
  pos=q+1
