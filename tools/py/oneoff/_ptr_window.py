from pathlib import Path
import struct
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes()
def off(r): return 0x702000+r-0xa16000
for base in (0xa155d0,0xa15600,0xa15630):
 print(hex(base))
 for i in range(0,0x40,4): print(hex(base+i),hex(struct.unpack_from("<I",D,off(base+i))[0]))

