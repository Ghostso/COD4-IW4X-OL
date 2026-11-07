import struct
from pathlib import Path
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes(); base=0x400000
# Find all source positions in likely code sections whose direct E8/E9 target is exactly one of template-adjacent RVAs.
T={0x36670,0x36675,0x3667a,0x36680,0x36689,0x36691,0x36697,0xaa176,0xaa17b,0xb2d90,0xb2d95}
pe=struct.unpack_from('<I',D,0x3c)[0]; n=struct.unpack_from('<H',D,pe+6)[0]; opt=pe+24; so=opt+struct.unpack_from('<H',D,pe+20)[0]
for i in range(n):
 h=so+40*i; nm=D[h:h+8].split(b'\0')[0].decode('latin1'); vs,va,rs,pr=struct.unpack_from('<IIII',D,h+8)
 if nm=='.tvm0' or not rs: continue
 b=D[pr:pr+rs]
 for j in range(len(b)-5):
  if b[j] in (0xe8,0xe9):
   a=va+j; t=a+5+struct.unpack_from('<i',b,j+1)[0]
   if t in T: print(hex(a),hex(b[j]),'->',hex(t),'sec',i,nm)
