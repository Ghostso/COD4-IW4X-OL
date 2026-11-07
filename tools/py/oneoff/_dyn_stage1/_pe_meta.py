import pefile, os
paths=[r'WeGame\tgp_daemon.exe',r'WeGame\client_launcher.exe',r'COD OL\WeGameLauncher\launcher.exe']
for p in paths:
    pe=pefile.PE(p,fast_load=True)
    print('\nFILE',p)
    print('machine',hex(pe.FILE_HEADER.Machine),'ts',hex(pe.FILE_HEADER.TimeDateStamp),'imagebase',hex(pe.OPTIONAL_HEADER.ImageBase),'sizeimage',hex(pe.OPTIONAL_HEADER.SizeOfImage),'entry',hex(pe.OPTIONAL_HEADER.ImageBase+pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    print('sections:')
    for s in pe.sections:
        print(' ',s.Name.rstrip(b'\0').decode('latin1'), 'VA',hex(pe.OPTIONAL_HEADER.ImageBase+s.VirtualAddress), 'VS',hex(s.Misc_VirtualSize), 'raw',hex(s.PointerToRawData),hex(s.SizeOfRawData), 'chars',hex(s.Characteristics))
