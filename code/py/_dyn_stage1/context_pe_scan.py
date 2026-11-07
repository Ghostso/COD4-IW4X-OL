from pathlib import Path
import pefile, re, struct
root=Path('.')
files=[root/'COD OL/codoMP_client_shipRetail.exe',root/'COD OL/codoMP_client_shipRetailBase.dll',root/'WeGame/tgp_daemon.exe',root/'COD OL/TCLS/Client.exe',root/'COD OL/TCLS/ClientBase.dll']
terms=[b'StartFor',b'AddPath',b'game_id',b'TCLS_SHAREDMEMEMORY',b'TCLS_TASMEMORY_',b'TCLSHOST_MUTEX',b'tcls_core',b'TCLSClient',b'TCLS logon',b'IsTCLSLogOn',b'WIN_NO_TCLS',b'CODO_TCLS_ZONE',b'codoMP_client_shipRetail',b'client.exe',b'launcher',b'WeGame',b'WeGameLauncher',b'..//WeGameLauncher//launcher.exe',b'CreateFileMapping',b'OpenFileMapping',b'MapViewOfFile',b'CreateMutex',b'OpenMutex',b'CreateNamedPipe',b'ConnectNamedPipe',b'WaitNamedPipe',b'GetCommandLine',b'GetEnvironmentVariable',b'CreateProcess',b'OpenProcess',b'RegOpenKey',b'RegQueryValue',b'FindWindow',b'SendMessage',b'GetCurrentProcessId']
apis=set(x.decode() for x in terms if re.fullmatch(rb'[A-Za-z][A-Za-z0-9]+',x))

def rva_to_off(pe,rva):
    try:return pe.get_offset_from_rva(rva)
    except:return None

def sec_for(pe,rva):
    for s in pe.sections:
        lo=s.VirtualAddress; hi=lo+max(s.Misc_VirtualSize,s.SizeOfRawData)
        if lo<=rva<hi:return s.Name.rstrip(b'\0').decode('ascii','replace'),lo,hi
    return None

for p in files:
    print('\n'+'='*100); print(p)
    if not p.exists():print('MISSING');continue
    pe=pefile.PE(str(p),fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    print('timestamp',hex(pe.FILE_HEADER.TimeDateStamp),'image',hex(pe.OPTIONAL_HEADER.SizeOfImage),'entry',hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    for ent in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
        dll=ent.dll.decode('ascii','replace')
        hits=[]
        for imp in ent.imports:
            n=imp.name.decode('ascii','replace') if imp.name else 'ord:'+str(imp.ordinal)
            if n in apis or any(k in n for k in ('CommandLine','Environment','Mapping','Mutex','Event','Pipe','Process','RegOpen','RegQuery','FindWindow','SendMessage')):
                hits.append((n,hex(imp.address)))
        if hits:
            print(' IMP',dll)
            for n,a in hits:print('   ',a,n)
    data=p.read_bytes()
    for term in terms:
        ptrn=term if term.isascii() else term
        hits=[]; start=0
        while True:
            i=data.find(ptrn,start)
            if i<0:break
            hits.append(i);start=i+1
            if len(hits)>=20:break
        if not hits:continue
        print(' TERM',term.decode('ascii','replace'),'raw hits',len(hits))
        for off in hits[:12]:
            # Find containing printable range and map to VA if possible
            lo=max(0,off-90); hi=min(len(data),off+len(term)+140)
            c=data[lo:hi]
            print('   raw',hex(off),repr(c[:280]))
    print(' SECTION MAP',[(s.Name.rstrip(b'\0').decode('ascii','replace'),hex(s.VirtualAddress),hex(s.SizeOfRawData)) for s in pe.sections])
