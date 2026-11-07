from pathlib import Path
import pefile
p=Path('COD OL/codoMP_client_shipRetail.exe')
pe=pefile.PE(str(p), fast_load=False)
data=p.read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase
rva=pe.OPTIONAL_HEADER.DATA_DIRECTORY[1].VirtualAddress
for s in pe.sections:
    if s.VirtualAddress <= rva < s.VirtualAddress+s.Misc_VirtualSize:
        off=s.PointerToRawData + (rva-s.VirtualAddress)
        break
print('raw import dir offset', off, 'size', pe.OPTIONAL_HEADER.DATA_DIRECTORY[1].Size)
count=0
while True:
    first=data[off:off+4]
    name=data[off+12:off+16]
    if first==b'\x00\x00\x00\x00':
        break
    count+=1
    try:
        dll=data[name[0]:name.index(0)+name[0:].index(0)+1].decode('ascii','replace')
    except Exception:
        dll='?'
    print(count, 'first', first.hex(), 'thunk_rva', hex(int.from_bytes(name,'little')), 'dll', dll)
    off+=20
print('count',count)
