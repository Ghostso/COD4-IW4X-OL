from pathlib import Path
import pefile
p=Path('COD OL/codoMP_client_shipRetail.exe'); pe=pefile.PE(str(p), fast_load=True); data=p.read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase
for va in [0xfff02da6,0x2e2200,0x662c5b78,0xf2c7f9b,0xfa0a58e,0x8ece83bd,0x12e24354,0xfe1e765,0xe1619d,0x20e1dfae,0xf13afc9,0x17fc9664,0xf6ac91df]:
    inside = base <= va < base + pe.OPTIONAL_HEADER.SizeOfImage
    print(hex(va), 'inside', inside)
