import pefile, struct, json, hashlib
from pathlib import Path
base=Path('COD OL')
for fn in ['codoMP_client_shipRetail.exe','codoMP_client_shipRetailBase.dll']:
    p=base/fn
    data=p.read_bytes()
    pe=pefile.PE(data=data,fast_load=True)
    print('===',fn,'===')
    print('sha',hashlib.sha256(data).hexdigest())
    print('base ep',hex(pe.OPTIONAL_HEADER.ImageBase),hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    print('dirs')
    for i,d in enumerate(pe.OPTIONAL_HEADER.DATA_DIRECTORY):
        if d.VirtualAddress or d.Size: print(i,hex(d.VirtualAddress),hex(d.Size))
    def rva2off(rva):
        for s in pe.sections:
            if s.VirtualAddress <= rva < s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
                return s.PointerToRawData+(rva-s.VirtualAddress)
        return None
    for name,rva in [('imp',pe.OPTIONAL_HEADER.DATA_DIRECTORY[1].VirtualAddress),('iat',pe.OPTIONAL_HEADER.DATA_DIRECTORY[12].VirtualAddress)]:
        off=rva2off(rva) if rva else None
        print(name,hex(rva) if rva else 0,'off',off)
        if off is not None: print('bytes',data[off:off+64].hex(' '))
    pe.parse_data_directories()
    print('parsed imports',[(e.dll.decode(errors='replace'),[hex(x.address) for x in e.imports]) for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[])])
    print('parsed iat',[(e.dll.decode(errors='replace'),[hex(x.address) for x in e.imports]) for e in getattr(pe,'DIRECTORY_ENTRY_IAT',[])])
    print('exports',len(getattr(pe,'DIRECTORY_ENTRY_EXPORT').symbols) if hasattr(pe,'DIRECTORY_ENTRY_EXPORT') else None)
