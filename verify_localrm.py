import pefile
pe=pefile.PE('D:\\BaiduNetdiskDownload\\使命召唤OL\\LocalRM.dll')
print('Machine:', hex(pe.FILE_HEADER.Machine), '(', 'I386' if pe.FILE_HEADER.Machine==0x14c else 'unknown', ')')
print('Number of sections:', pe.FILE_HEADER.NumberOfSections)
print('SizeOfImage:', hex(pe.OPTIONAL_HEADER.SizeOfImage))
print('Characteristics:', hex(pe.FILE_HEADER.Characteristics), 'DLL' if pe.FILE_HEADER.Characteristics & 0x2000 else 'not DLL')
if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
    print('Export directory found')
    print('NumberOfFunctions:', pe.DIRECTORY_ENTRY_EXPORT.struct.NumberOfFunctions)
    print('NumberOfNames:', pe.DIRECTORY_ENTRY_EXPORT.struct.NumberOfNames)
    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if exp.name:
            try:
                name = exp.name.decode('utf-8')
            except:
                name = str(exp.name)
            print(f'  {name} (ordinal {exp.ordinal}) at RVA {exp.address:#x}')
else:
    print('No export directory')