from pathlib import Path
import pefile
p=Path('COD OL/codoMP_client_shipRetail.exe')
pe=pefile.PE(str(p), fast_load=True)
for rva in [0xe5dc635, 0xe9dc665]:
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress+s.Misc_VirtualSize:
            off=s.PointerToRawData+(rva-s.VirtualAddress)
            print(hex(rva), s.Name.rstrip(b'\x00').decode('latin1','replace'), hex(off), hex(s.Characteristics))
            break
