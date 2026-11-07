import pefile, os
for p in [r'WeGame\tgp_daemon.exe', r'WeGame\client_launcher.exe']:
    pe=pefile.PE(p,fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    print('\n###',p)
    for ent in pe.DIRECTORY_ENTRY_IMPORT:
        print('\n',ent.dll.decode('latin1'))
        for imp in ent.imports:
            n=(imp.name or b'').decode('latin1') if imp.name else f'ord{imp.ordinal}'
            if any(k.lower() in n.lower() for k in ['process','environment','commandline','file','mapping','pipe','event','mutex','registry','reg','socket','connect','module','winexec','shell','thread','token','instance','authenticate','security']):
                print(f'  {n:35s} IAT {pe.OPTIONAL_HEADER.ImageBase+imp.address:08X}')
