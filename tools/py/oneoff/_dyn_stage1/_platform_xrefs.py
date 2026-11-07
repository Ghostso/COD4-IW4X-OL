import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_MEM

paths = [
    r'COD OL\WeGameLauncher\launcher.exe',
    r'WeGame\tgp_daemon.exe',
    r'WeGame\wegame.exe',
]
apis = {
    'GetCommandLineW','CommandLineToArgvW','GetEnvironmentVariableW','CreateFileMappingW','CreateFileMappingA',
    'OpenFileMappingA','CreateProcessW','CreateMutexA','OpenProcess','Process32First','Process32Next',
    'Process32FirstW','Process32NextW','OpenEventA','CreateEventA','CreateEventW','PeekNamedPipe','ShellExecuteExW',
    'FindWindowA','FindWindowW','SendMessageA','RegOpenKeyExW','RegQueryValueExW','WaitForSingleObject',
    'WaitForMultipleObjects','CreateToolhelp32Snapshot','Module32FirstW','Module32NextW','GetExitCodeProcess',
    'GetCurrentProcessId','OpenMutexA','CreateMutexW','OpenMutexW','CreatePipe','ConnectNamedPipe','CallNamedPipeW',
    'SetEvent','OpenEventW','ReleaseMutex'
}

for path in paths:
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    imports = {}
    for ent in pe.DIRECTORY_ENTRY_IMPORT:
        dll = ent.dll.decode(errors='replace')
        for imp in ent.imports:
            if imp.name:
                name = imp.name.decode(errors='replace')
                if name in apis or 'Process' in name or 'FileMapping' in name or 'NamedPipe' in name or 'Event' in name or 'Mutex' in name:
                    imports[imp.address] = (dll, name)
    print('='*100)
    print('FILE', path, 'base', hex(pe.OPTIONAL_HEADER.ImageBase), 'entry', hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    print('IAT targets:')
    for a,(dll,name) in sorted(imports.items()):
        print(f'  {a:08X} {dll}!{name}')

    text_ranges=[]
    for sec in pe.sections:
        if sec.Characteristics & 0x20000000:
            data = sec.get_data()
            va = pe.OPTIONAL_HEADER.ImageBase + sec.VirtualAddress
            text_ranges.append((va, va+len(data), data, sec.Name.rstrip(b'\0').decode(errors='replace')))

    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    hits=[]
    for va, vend, data, sn in text_ranges:
        for ins in md.disasm(data, va):
            if ins.address >= vend: break
            ops=[]
            for op in ins.operands:
                if op.type == CS_OP_MEM and op.mem.base == 0 and op.mem.index == 0 and op.mem.disp in imports:
                    ops.append(op.mem.disp)
            if ops:
                hits.append((ins.address, ins.mnemonic, ins.op_str, ops))
    print('XREFS', len(hits))
    for a,m,o,ops in hits:
        print(f'  {a:08X}: {m} {o} -> ' + ','.join(f'{x:08X}:{imports[x][0]}!{imports[x][1]}' for x in ops))
