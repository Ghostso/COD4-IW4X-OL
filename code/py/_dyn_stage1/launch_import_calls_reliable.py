from pathlib import Path 
import pefile, struct, json 
from capstone import Cs, CS_ARCH_X86, CS_MODE_32 
from capstone.x86 import X86_OP_MEM, X86_OP_IMM 
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL') 
FILES=[ROOT/'COD OL'/'TCLS'/'Client.exe', ROOT/'COD OL'/'WeGameLauncher'/'launcher.exe', ROOT/'COD OL'/'codoMP_client_shipRetail.exe'] 
WATCH={'CreateProcessW','CreateProcessA','ShellExecuteExW','ShellExecuteW','GetCommandLineA','GetCommandLineW','GetEnvironmentVariableA','GetEnvironmentVariableW','CreateFileW','CreateFileA','OpenFileMappingW','OpenFileMappingA','CreateFileMappingW','CreateFileMappingA','MapViewOfFile','OpenMutexW','OpenMutexA','CreateMutexW','CreateMutexA','CreateNamedPipeW','CreateNamedPipeA','ConnectNamedPipe','RegOpenKeyExW','RegOpenKeyExA','RegQueryValueExW','RegQueryValueExA'} 
def read_cstr(pe,data,va,n=300): 
    try: off=pe.get_offset_from_rva(va-pe.OPTIONAL_HEADER.ImageBase) 
    except Exception: return None 
    if off<0 or off>=len(data): return None 
    end=data.find(b'\0',off,min(len(data),off+n)) 
    if end<0: return None 
    b=data[off:end] 
    if not b: return '' 
    printable=sum(32<=x<127 or x in (9,10,13) for x in b) 
    if printable/len(b)<0.85: return None 
    return b.decode('latin1','replace') 
out=[] 
for path in FILES: 
    data=path.read_bytes() 
    pe=pefile.PE(data=data,fast_load=True) 
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']]) 
    base=pe.OPTIONAL_HEADER.ImageBase 
    iat={} 
    for ent in pe.DIRECTORY_ENTRY_IMPORT: 
        for imp in ent.imports: 
            if imp.name: iat[imp.address]=ent.dll.decode('latin1','replace')+'!'+imp.name.decode('latin1','replace') 
    text=next((s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text'),None) 
    if text is None: continue 
    raw=text.get_data(); start=base+text.VirtualAddress 
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True 
    ins=list(md.disasm(raw,start)) 
    out.append(f'FILE {path} base={base:#x} text={start:#x}-{start+len(raw):#x} imports={len(iat)}') 
    for idx,i in enumerate(ins): 
        if i.mnemonic!='call' or not i.operands: continue 
        op=i.operands[0] 
        target=None 
        if op.type==X86_OP_MEM and op.mem.base==0 and op.mem.index==0 and op.mem.disp in iat: 
            target=iat[op.mem.disp] 
        if target not in WATCH: continue 
        out.append('='*100) 
        out.append(f'CALL {i.address:08X} RVA={i.address-base:08X} -> {target}') 
        for j in ins[max(0,idx-70):min(len(ins),idx+30)]: 
            mark='>>' if j.address==i.address else '  ' 
            ann='' 
            if j.mnemonic.startswith('push') and j.operands: 
                o=j.operands[0] 
                if o.type==X86_OP_IMM: 
                    s=read_cstr(pe,data,o.imm) 
                    if s is not None: ann=' ; '+repr(s) 
            out.append(f'{mark}{j.address-base:08X} {j.bytes.hex():<20} {j.mnemonic:<8} {j.op_str}{ann}') 
    out.append('') 
(ROOT/'_dyn_stage1'/'launch_import_calls_reliable.txt').write_text('\n'.join(out),encoding='utf-8') 
print('\n'.join(out[:100])) 
