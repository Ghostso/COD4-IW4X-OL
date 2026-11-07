from pathlib import Path
import pefile
fn=r'COD OL/TCLS/Client.exe'
p=pefile.PE(fn,fast_load=True)
D=Path(fn).read_bytes()
for rva in [0x1238,0x1e78,0x3712,0x1000]:
    s=next(x for x in p.sections if x.VirtualAddress<=rva<x.VirtualAddress+min(x.Misc_VirtualSize,x.SizeOfRawData))
    off=s.PointerToRawData+rva-s.VirtualAddress
    print(hex(rva),hex(off),D[off:off+32].hex())

