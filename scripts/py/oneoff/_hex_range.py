import struct
from pathlib import Path
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes()
for start,end in ((0x36500,0x36600),(0x36600,0x36750)):
 print('===',hex(start),'===')
 for off in range(start,end,16):
  b=D[off:off+16]
  hx=' '.join(f'{x:02x}' for x in b)
  asc=''.join(chr(x) if 32<=x<127 else '.' for x in b)
  print(f'{off:08X}  {hx:<47}  {asc}')
