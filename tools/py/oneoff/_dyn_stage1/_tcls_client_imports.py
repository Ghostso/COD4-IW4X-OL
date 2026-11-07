import pefile, capstone, struct, sys
from pathlib import Path
p=Path(r'COD OL\TCLS\Client.exe')
pe=pefile.PE(str(p), fast_load=False)
ib=pe.OPTIONAL_HEADER.ImageBase
print('IMAGEBASE',hex(ib),'ENTRY',hex(ib+pe.OPTIONAL_HEADER.AddressOfEntryPoint),'SIZE',hex(pe.OPTIONAL_HEADER.SizeOfImage))
for s in pe.sections:
    print('SEC',s.Name.decode(errors='replace').rstrip('\0'),hex(ib+s.VirtualAddress),hex(ib+s.VirtualAddress+s.Misc_VirtualSize),hex(s.PointerToRawData),hex(s.SizeOfRawData),hex(s.Characteristics))
print('IMPORTS')
for e in pe.DIRECTORY_ENTRY_IMPORT:
    print(e.dll.decode(errors='replace'))
    for i in e.imports:
        print(' ',hex(i.address),i.name.decode(errors='replace') if i.name else ('ord'+str(i.ordinal)))
