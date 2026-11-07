import pefile
for n in ['TenRpcs.dll','VSDDrvDll.dll']:
    p=r'COD OL\\'+n
    pe=pefile.PE(p)
    print('\n===',n)
    for e in pe.DIRECTORY_ENTRY_IMPORT:
        dll=e.dll.decode(errors='replace').lower()
        if dll in ('ws2_32.dll','winhttp.dll'):
            print(' ',e.dll.decode(),len(e.imports))
            print('   ',', '.join(i.name.decode(errors='replace') if i.name else 'ord%d'%i.ordinal for i in e.imports))
