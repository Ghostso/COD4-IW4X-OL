from pathlib import Path
import pefile
p=Path('COD OL/codoMP_client_shipRetail.exe')
pe=pefile.PE(str(p), fast_load=True)
data=p.read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase

def off_by_va(va):
    rva=va-base
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress+s.Misc_VirtualSize:
            return s.PointerToRawData + (rva-s.VirtualAddress)
    return None
print('entry_rva',hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),'entry_off',off_by_va(base+pe.OPTIONAL_HEADER.AddressOfEntryPoint))
print('import_descr_off',off_by_va(0x0E9DC635),'iat_va_off',off_by_va(0x0E9DC665))
print('entry_bytes',data[off_by_va(base+pe.OPTIONAL_HEADER.AddressOfEntryPoint):off_by_va(base+pe.OPTIONAL_HEADER.AddressOfEntryPoint)+16].hex(' '))
print('descr_bytes',data[off_by_va(0x0E9DC635):off_by_va(0x0E9DC635)+48].hex(' '))
print('iat_bytes',data[off_by_va(0x0E9DC665):off_by_va(0x0E9DC665)+16].hex(' '))
