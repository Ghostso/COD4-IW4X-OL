import pefile
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
pe=pefile.PE(p,fast_load=True); pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
want={0x100d825c,0x100d8260,0x100d8250,0x100d8254}
for d in pe.DIRECTORY_ENTRY_IMPORT:
    for imp in d.imports:
        if imp.address in want:
            print('%08X  %s!%s'%(imp.address,d.dll.decode(),imp.name.decode() if imp.name else 'ord%d'%imp.ordinal))
print()
# list all msvcrt imports with addresses for reference
for d in pe.DIRECTORY_ENTRY_IMPORT:
    nm=d.dll.decode().lower()
    if 'msvc' in nm or 'crt' in nm:
        print('== %s =='%d.dll.decode())
        for imp in d.imports[:60]:
            print('  %08X %s'%(imp.address,imp.name.decode() if imp.name else 'ord'))
