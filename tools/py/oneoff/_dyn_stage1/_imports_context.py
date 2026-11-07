import pefile,struct
for fn in [r'WeGame/tgp_daemon.exe',r'COD OL/WeGameLauncher/launcher.exe',r'WeGame/wegame.exe']:
    p=pefile.PE(fn,fast_load=True)
    print('FILE',fn,'IMAGE',hex(p.OPTIONAL_HEADER.ImageBase),'SIZE',hex(p.OPTIONAL_HEADER.SizeOfImage),'ENTRY',hex(p.OPTIONAL_HEADER.AddressOfEntryPoint))
    p.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    for e in p.DIRECTORY_ENTRY_IMPORT:
        for i in e.imports:
            n=i.name.decode(errors='replace') if i.name else str(i.ordinal)
            if n in ['GetCommandLineW','CommandLineToArgvW','GetEnvironmentVariableW','CreateFileMappingW','CreateProcessW','CreateMutexA','OpenProcess','FindWindowA','FindWindowW','SendMessageA','RegOpenKeyExW','RegQueryValueExW','Process32First','Process32Next','Process32FirstW','Process32NextW','OpenFileMappingA','CreateFileMappingA','OpenEventA','CreateEventA','PeekNamedPipe','ShellExecuteExW']:
                print(hex(i.address),e.dll.decode(errors='replace'),n)

