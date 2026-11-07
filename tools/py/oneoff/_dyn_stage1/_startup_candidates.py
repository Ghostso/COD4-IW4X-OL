from pathlib import Path
import pefile, struct, re

files = [
    Path(r'WeGame/tgp_daemon.exe'),
    Path(r'WeGame/wegame.exe'),
    Path(r'WeGame/WGLogin.dll'),
    Path(r'COD OL/TCLS/Client.exe'),
    Path(r'COD OL/TCLS/TCLSClient.dll'),
    Path(r'COD OL/TCLS/ClientBase.dll'),
    Path(r'COD OL/TCLS/TPSvc.exe'),
    Path(r'COD OL/TCLS/tpsvcBase.dll'),
    Path(r'COD OL/codoMP_client_shipRetail.exe'),
    Path(r'COD OL/codoMP_client_shipRetailBase.dll'),
]
apis = [
    'GetCommandLine','CommandLineToArgv','GetEnvironmentVariable','CreateFileMapping','OpenFileMapping','MapViewOfFile',
    'CreateMutex','OpenMutex','CreateEvent','OpenEvent','CreateNamedPipe','ConnectNamedPipe','WaitNamedPipe',
    'CreateProcess','OpenProcess','RegOpenKey','RegQueryValue','RegGetValue','FindWindow','SendMessage',
    'CreateFile','ReadFile','WriteFile','DeviceIoControl','GetLastError','LoadLibrary','GetProcAddress'
]
terms = [b'AddPath',b'StartFor',b'game_id',b'launcher',b'launch',b'session',b'context',b'platform',b'account',b'token',b'ticket',b'auth',b'ipc',b'pipe',b'instance',b'environment',b'TCLS',b'TCLSHOST',b'tcls_core',b'TCLS_SHARED',b'SHAREDMEM',b'TP3GameGuard',b'XTDL2',b'CODOL',b'codoMP',b'pid',b'PID']

def ascii_hits(data, needle, width=100, maxhits=8):
    out=[]; start=0
    low=data.lower(); n=needle.lower()
    while len(out)<maxhits:
        i=low.find(n,start)
        if i<0: break
        out.append((i,data[max(0,i-width):i+len(needle)+width]))
        start=i+1
    return out

for f in files:
    print('\n'+'='*100)
    print(f, f.exists(), f.stat().st_size if f.exists() else '')
    if not f.exists(): continue
    try:
        pe=pefile.PE(str(f), fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
        imps={}
        if hasattr(pe,'DIRECTORY_ENTRY_IMPORT'):
            for ent in pe.DIRECTORY_ENTRY_IMPORT:
                dll=ent.dll.decode('ascii','replace')
                imps[dll]=[imp.name.decode('ascii','replace') if imp.name else '#'+str(imp.ordinal) for imp in ent.imports]
        flat=[x for v in imps.values() for x in v]
        print('sections:', [(s.Name.rstrip(b'\0').decode('ascii','replace'),hex(s.VirtualAddress),hex(s.SizeOfRawData)) for s in pe.sections])
        print('timestamp',hex(pe.FILE_HEADER.TimeDateStamp),'image',hex(pe.OPTIONAL_HEADER.SizeOfImage),'entry',hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
        print('api matches:', sorted(set(a for a in apis if a in flat)))
        for dll,names in imps.items():
            m=sorted(set(n for n in names if any(k.lower() in n.lower() for k in ['commandline','environment','mapping','mutex','event','namedpipe','process','regopen','regquery','findwindow','sendmessage','connect','deviceio'])))
            if m: print(' ',dll,m)
        data=f.read_bytes()
        for t in terms:
            hits=ascii_hits(data,t)
            if hits:
                print('term',t.decode('ascii','replace'),'hits',len(hits))
                for off,ctx in hits[:3]: print(' ',hex(off),repr(ctx))
    except Exception as e:
        print('ERROR',type(e).__name__,e)
