import pefile,os,re
for name in ['TenProxy.dll','TenRpcs.dll','GameRpcs.dll','GameDataPlatformServer.dll','TCJ.dll','TenSLX.dll','VSDDrvDll.dll']:
    p=os.path.join('COD OL',name)
    try:
        pe=pefile.PE(p,fast_load=True)
    except Exception as e:
        print(name,'ERR',e); continue
    print('\n=========',name,'size',os.path.getsize(p),'imagebase',hex(pe.OPTIONAL_HEADER.ImageBase),'ep',hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    if hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):
        syms=pe.DIRECTORY_ENTRY_EXPORT.symbols
        print(' exports',len(syms))
        for s in syms[:60]:
            print('   ',hex(s.address),s.name.decode(errors='replace') if s.name else 'ord#%d'%s.ordinal)
    else: print(' exports NONE')
    if hasattr(pe,'DIRECTORY_ENTRY_IMPORT'):
        print(' imports:',', '.join(e.dll.decode(errors='replace') for e in pe.DIRECTORY_ENTRY_IMPORT))
    else: print(' imports NONE')
