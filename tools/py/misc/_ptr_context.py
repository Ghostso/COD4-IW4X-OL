import struct
from pathlib import Path
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); pe=struct.unpack_from("<I",D,0x3c)[0]; opt=pe+24
# hardcoded section map from PE
secs=[(0x1000,0x8a689a,0x1000,0x593000),(0x8a8000,0x16da70,0x594000,0x16e000),(0xa16000,0xdbb1cc0,0x702000,0x62000),(0xe5c8000,0x31,0x764000,0x1000),(0xe5c9000,0x9228,0x765000,0xa000),(0xe5d3000,0x4000,0x76f000,0x2000),(0xe5d7000,0x82000,0x771000,0x6000)]
def off(r):
 for va,vs,pr,rs in secs:
  if va<=r<va+rs:return pr+r-va
for r in (0xa15614,0x1cd5ef8,0x1cd5efc,0xca8114,0xca8194):
 o=off(r)
 print(hex(r),hex(o) if o is not None else None, D[o-32:o+64].hex() if o is not None else "")
 if o is not None:
  print("dwords",[hex(struct.unpack_from("<I",D,o-32+4*i)[0]) for i in range(16)])

