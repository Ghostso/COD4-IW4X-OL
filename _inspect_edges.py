import struct
from pathlib import Path
p=Path("COD OL/codoMP_client_shipRetail.exe"); d=p.read_bytes()
for r,n in ((0x3667a,160),(0x36691,200),(0x269ae,160),(0x269c6,160),(0xaa17b,160),(0xaa192,160),(0xb2d95,160),(0xb2dac,160),(0x21da25,160),(0x21da3c,160)):
 print("TARGET",hex(r)); print(d[r-80:r+n].hex()); print()

