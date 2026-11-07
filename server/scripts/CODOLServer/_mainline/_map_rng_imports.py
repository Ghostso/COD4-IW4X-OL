import pefile
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
pe=pefile.PE(p,fast_load=True); pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
want={0x10085340,0x10085346,0x10085310,0x10085382,0x10085340}
for d in pe.DIRECTORY_ENTRY_IMPORT:
    for imp in d.imports:
        if imp.address in want:
            print('thunk %08X -> %s!%s'%(imp.address,d.dll.decode(),imp.name.decode() if imp.name else 'ord'))
# also list all import thunks near 0x85300-0x85390
print('\nnearby imports:')
for d in pe.DIRECTORY_ENTRY_IMPORT:
    for imp in d.imports:
        if 0x10085300 <= imp.address <= 0x100853A0:
            print('  %08X %s!%s'%(imp.address,d.dll.decode(),imp.name.decode() if imp.name else 'ord'))
