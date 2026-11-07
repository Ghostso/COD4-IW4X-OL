import pefile, os
root=r'COD OL'
names=['TenRpcs.dll','GameRpcs.dll','TenProxy.dll','VSDDrvDll.dll','TCJ.dll','TenSLX.dll','GameDataPlatformServer.dll','BugTrace.dll','TerSafe.dll','PolicyProbe.dll']
for name in names:
    p=os.path.join(root,name)
    if not os.path.exists(p): continue
    try: pe=pefile.PE(p)
    except Exception as e: print(name,'ERR',e); continue
    print('\n=====',name,os.path.getsize(p))
    if hasattr(pe,'DIRECTORY_ENTRY_IMPORT'):
        for e in pe.DIRECTORY_ENTRY_IMPORT:
            dll=e.dll.decode(errors='replace')
            if dll.lower() in ('ws2_32.dll','winhttp.dll','wininet.dll','iphlpapi.dll'):
                print(' ',dll,':',', '.join((i.name.decode(errors='replace') if i.name else 'ord%d'%i.ordinal) for i in e.imports))
