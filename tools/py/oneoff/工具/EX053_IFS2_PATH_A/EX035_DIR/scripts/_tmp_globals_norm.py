from pathlib import Path
import struct
r=Path("codoMP_client_shipRetail.exe").read_bytes()
for va in [0x7886E60,0x7886E68,0x7886E6C,0x81AA110,0x81AA114,0x1CD5EF8,0x1CD5EFC,0xC9EFC34,0xC9EFC38,0xC9FFD54,0xC9FFD58]:
    o=(va-0x400000)%len(r)
    b=r[o:o+32]
    print(hex(va),hex(o),[hex(struct.unpack_from("<I",b,k)[0]) for k in range(0,32,4)])
