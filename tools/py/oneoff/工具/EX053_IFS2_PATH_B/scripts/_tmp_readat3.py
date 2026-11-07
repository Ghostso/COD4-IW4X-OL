from pathlib import Path
r=Path("codoMP_client_shipRetail.exe").read_bytes()
for x in [0x7886E60,0x7886E68,0x7886E6C,0x81AA110,0x81AA114,0x1CD5EF8,0x1CD5EFC,0xC9EFC34,0xC9EFC38,0xC9FFD54,0xC9FFD58]:
    off=(x-0x400000)%len(r)
    print(hex(x),hex(off),r[off:off+16].hex())
