from pathlib import Path
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes()
for base in (0x36670,0xaa176,0xb2d90,0x269ae,0x21da25):
 print('===',hex(base),'===')
 print(D[base:base+80].hex(' '))
