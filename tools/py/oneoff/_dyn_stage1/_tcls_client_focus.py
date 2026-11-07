from pathlib import Path
import pefile, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
p = Path(r'COD OL/TCLS/Client.exe')
data = p.read_bytes(); pe = pefile.PE(data=data, fast_load=True); base = pe.OPTIONAL_HEADER.ImageBase
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
terms=[b'StartFor',b'cmd_launcher_info.ini',b'cmd_start_for.ini',b'game_id',b'launcher=',b'client_launcher.exe',b'codoMP_client_shipRetail.exe',b'TCLS_SHAREDMEMEMORY',b'TASLogin',b'TP3GameGuardShareMapping',b'mmog_data.xml',b'GetCommandLineW',b'CreateProcessW',b'ShellExecuteExW']
print('FILE',p,'base',hex(base),'size',len(data))
print('IMPORTS')
try:
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    for ent in pe.DIRECTORY_ENTRY_IMPORT:
        names=[]
        for imp in ent.imports:
            if imp.name in (b'CreateProcessW',b'CreateProcessA',b'ShellExecuteExW',b'GetCommandLineW',b'GetCommandLineA',b'OpenFileMappingW',b'OpenFileMappingA',b'CreateFileMappingW',b'CreateFileMappingA',b'CreateFileW',b'CreateFileA',b'GetEnvironmentVariableW',b'GetEnvironmentVariableA',b'CreateMutexW',b'CreateMutexA',b'ConnectNamedPipe',b'CreateNamedPipeW',b'CreateNamedPipeA',b'OpenMutexW',b'OpenMutexA',b'OpenEventW',b'OpenEventA'):
                names.append(imp.name.decode('latin1'))
        if names: print(ent.dll.decode('latin1'),sorted(set(names)))
except Exception as e: print('import parse',e)
secs=[(base+s.VirtualAddress,base+s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData),s.Name.rstrip(b'\0').decode('latin1')) for s in pe.sections]
def sec_for(va): return next((n for a,b,n in secs if a<=va<b),'?')
def cstr(va,maxn=220):
    try: off=pe.get_offset_from_rva(va-base)
    except Exception: return None
    if off<0 or off>=len(data): return None
    end=data.find(b'\0',off,min(len(data),off+maxn))
    if end<0: end=min(len(data),off+maxn)
    b=data[off:end]
    if not b:return ''
    pr=sum((32<=x<127) or x in (9,10,13) for x in b)/len(b)
    return b.decode('latin1','replace') if pr>.8 else None
for term in terms:
    offs=[]; start=0
    while True:
        i=data.find(term,start)
        if i<0: break
        offs.append(i); start=i+1
    print('\n###',term.decode('latin1'),'raw',[hex(x) for x in offs[:20]],'count',len(offs))
    vaset=set()
    for off in offs[:20]:
        try: vaset.add(base+pe.get_rva_from_offset(off))
        except Exception: pass
    for va in sorted(vaset):
        refs=[]; start=0
        for size in (4,):
            ptr=struct.pack('<I',va)
            while True:
                i=data.find(ptr,start)
                if i<0: break
                refs.append(i); start=i+1
        for roff in refs[:30]:
            try: rva=pe.get_rva_from_offset(roff)
            except Exception: continue
            print('\nREF strVA',hex(va),'file',hex(roff),'RVA',hex(rva),'sec',sec_for(base+rva))
            lo=max(0,roff-90); hi=min(len(data),roff+150)
            try: rlo=pe.get_rva_from_offset(lo); rhi=pe.get_rva_from_offset(hi)
            except Exception: continue
            for ins in md.disasm(data[lo:hi],base+rlo):
                mark='>>' if ins.address==base+rva else '  '
                ann=''
                if ins.mnemonic.startswith('push') and ins.operands and ins.operands[0].type==3:
                    s=cstr(ins.operands[0].imm)
                    if s is not None: ann=' ; '+repr(s)
                print(f'{mark}{ins.address-base:08X} {ins.bytes.hex():<20} {ins.mnemonic:<8} {ins.op_str}{ann}')
