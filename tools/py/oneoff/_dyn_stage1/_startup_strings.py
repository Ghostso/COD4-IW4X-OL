from pathlib import Path
import pefile, re, json

files = [Path(r'COD OL/codoMP_client_shipRetail.exe'),Path(r'COD OL/codoMP_client_shipRetailBase.dll'),Path(r'WeGame/tgp_daemon.exe'),Path(r'COD OL/TCLS/Client.exe'),Path(r'COD OL/TCLS/ClientBase.dll')]
apis_wanted = ['GetCommandLineA','GetCommandLineW','CommandLineToArgvW','GetEnvironmentVariableW','GetEnvironmentStringsW','CreateFileMappingW','OpenFileMappingW','MapViewOfFile','CreateMutexA','CreateMutexW','OpenMutexA','OpenMutexW','CreateEventA','CreateEventW','OpenEventA','OpenEventW','CreateNamedPipeA','CreateNamedPipeW','ConnectNamedPipe','WaitNamedPipeA','WaitNamedPipeW','CreateProcessA','CreateProcessW','OpenProcess','RegOpenKeyExA','RegOpenKeyExW','RegQueryValueExA','RegQueryValueExW','RegGetValueA','RegGetValueW','FindWindowA','FindWindowW','SendMessageA','SendMessageW','GetModuleFileNameA','GetModuleFileNameW','GetCurrentProcessId']

def raw_strings(data, minlen=4):
    out=[]
    # ascii
    for m in re.finditer(rb'[ -~]{4,}', data):
        try: out.append((m.start(), m.group().decode('ascii')))
        except: pass
    # utf16le allowing CJK/nonascii but printable based on categories
    i=0
    while i+2<=len(data):
        j=i; chars=[]
        while j+2<=len(data):
            c=data[j] | (data[j+1]<<8)
            if c==0: break
            ch=chr(c)
            if ch=='\r' or ch=='\n' or ch=='\t' or (ch.isprintable() and c>=0x20):
                chars.append(ch); j+=2
            else: break
        if j-i>=8 and len(chars)>=4:
            out.append((i,''.join(chars)))
            i=j
        else: i+=2
    return out

for p in files:
    print('\n'+'#'*90); print(p)
    if not p.exists(): print('MISSING'); continue
    pe=pefile.PE(str(p),fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    print('ts',hex(pe.FILE_HEADER.TimeDateStamp),'image',hex(pe.OPTIONAL_HEADER.SizeOfImage),'entry',hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    for ent in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
        dll=ent.dll.decode('ascii','replace'); names=[x.name.decode('ascii','replace') if x.name else '#'+str(x.ordinal) for x in ent.imports]
        hit=[n for n in names if n in apis_wanted]
        if hit: print('IMPORT',dll,hit)
    data=p.read_bytes(); ss=raw_strings(data)
    pats=['TCLS','Client.exe','client.exe','StartFor','AddPath','launcher','Launcher','cmd_launcher','fatal','Fatal','FATAL','error','Error','ERROR','TCLSClient','shared','Shared','mutex','Mutex','pipe','Pipe']
    for pat in pats:
        hits=[(o,s) for o,s in ss if pat.lower() in s.lower()]
        if hits:
            print('--',pat,len(hits))
            for o,s in hits[:15]: print(hex(o),repr(s[:400]))
