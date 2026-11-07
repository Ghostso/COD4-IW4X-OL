from pathlib import Path
import struct
vals=[0x7886E60,0x7886E68,0x7886E6C,0x7886E70,0x81AA110,0x81AA114,0x81A5270,0x81A5468,0x81A55A0,0x1CD5EF8,0x1CD5EFC,0xC9EFC34,0xC9EFC38,0xC9FFD54,0xC9FFD58]
path=Path('codoMP_client_shipRetail.exe')
for va in vals:
 rva=va-0x400000
 # normalized absolute-file offset used by current extractor
 o=rva
 print(hex(va),'normoff',hex(o),end=' ')
 try:
  with path.open('rb') as f:f.seek(o);b=f.read(32)
  print(b.hex(),[hex(struct.unpack_from('<I',b,k)[0]) for k in range(0,32,4)])
 except Exception as e: print(type(e).__name__,e)
