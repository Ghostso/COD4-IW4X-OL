import pefile,os
for name in ['TenProxy.dll','TenRpcs.dll','GameRpcs.dll','GameDataPlatformServer.dll']:
    p=os.path.join('COD OL',name)
    pe=pefile.PE(p)
    print('\n=========',name)
    if hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):
        print('exports',len(pe.DIRECTORY_ENTRY_EXPORT.symbols))
        for s in pe.DIRECTORY_ENTRY_EXPORT.symbols[:80]:
            print('  ',hex(s.address),s.name.decode(errors='replace') if s.name else s.ordinal)
    if hasattr(pe,'DIRECTORY_ENTRY_IMPORT'):
        for e in pe.DIRECTORY_ENTRY_IMPORT:
            print(' import',e.dll.decode(errors='replace'),len(e.imports))
            for imp in e.imports[:20]: print('    ',imp.name.decode(errors='replace') if imp.name else imp.ordinal)
