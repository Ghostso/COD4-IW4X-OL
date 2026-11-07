from pathlib import Path
import pefile, struct, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_OP_IMM, X86_OP_REG
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
FILES=[
    ROOT/'WeGame'/'tgp_daemon.exe',
    ROOT/'WeGame'/'client_launcher.exe',
    ROOT/'COD OL'/'TCLS'/'Client.exe',
    ROOT/'WeGame'/'wegame.exe',
]
WATCH={'CreateProcessW','CreateProcessA','ShellExecuteExW','ShellExecuteW','GetCommandLineW','GetCommandLineA','GetEnvironmentVariableW','GetEnvironmentVariableA','CreateFileMappingW','CreateFileMappingA','OpenFileMappingW','OpenFileMappingA','MapViewOfFile','OpenMutexW','OpenMutexA','CreateMutexW','CreateMutexA','CreateNamedPipeW','CreateNamedPipeA','ConnectNamedPipe','RegOpenKeyExW','RegOpenKeyExA','RegQueryValueExW','RegQueryValueExA','CreateFileW','CreateFileA'}
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True

def cstr(pe,data,va,n=500):
    try:
        off=pe.get_offset_from_rva(va-pe.OPTIONAL_HEADER.ImageBase)
    except Exception:
        return None
    if not (0<=off<len(data)): return None
    end=data.find(b'\0',off,min(len(data),off+n))
    if end<0: return None
    b=data[off:end]
    if not b: return ''
    ok=sum(32<=x<127 or x in (9,10,13) for x in b)
    if ok/len(b)<0.78: return None
    return b.decode('latin1','replace')

out=[]
for path in FILES:
    if not path.exists():
        out.append(f'MISSING {path}'); continue
    data=path.read_bytes()
    pe=pefile.PE(data=data,fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    base=pe.OPTIONAL_HEADER.ImageBase
    imports={}
    for ent in pe.DIRECTORY_ENTRY_IMPORT:
        dll=ent.dll.decode('latin1','replace')
        for imp in ent.imports:
            if imp.name:
                imports[imp.address]=(dll,imp.name.decode('latin1','replace'))
    code_sections=[]
    for sec in pe.sections:
        if sec.Characteristics & 0x20000000:
            raw=sec.get_data(); start=base+sec.VirtualAddress
            code_sections.append((start,start+len(raw),sec.Name.rstrip(b'\0').decode('latin1','replace')))
    # Find import thunks: ff 25 [iat] or e9 rel32 thunk maybe jmp again.
    thunks={}
    allins=[]
    for start,end,sn in code_sections:
        off=pe.get_offset_from_rva(start-base)
        raw=data[off:off+(end-start)]
        ins=list(md.disasm(raw,start))
        allins += [(start,end,sn,x) for x in ins]
        for j,x in enumerate(ins):
            if x.mnemonic=='jmp' and len(x.operands)==1:
                op=x.operands[0]
                if op.type==X86_OP_MEM and op.mem.base==0 and op.mem.index==0 and op.mem.disp in imports:
                    thunks[x.address]=op.mem.disp
    out.append('='*120)
    out.append(f'FILE {path.name} size={len(data):#x} base={base:#x} ts={pe.FILE_HEADER.TimeDateStamp:#x} image={pe.OPTIONAL_HEADER.SizeOfImage:#x}')
    out.append(f'IMPORTS total={len(imports)} watched={sum(1 for d,n in imports.values() if n in WATCH)} thunks={len(thunks)}')
    for va,(dll,name) in sorted(imports.items()):
        if name in WATCH:
            out.append(f'  IAT {va:#010x} {dll}!{name}')
    # identify instructions that reference watched import or call thunk
    byaddr={x.address:x for _,_,_,x in allins}
    hits=[]
    for start,end,sn,x in allins:
        refs=[]; target=None
        for op in x.operands:
            if op.type==X86_OP_MEM and op.mem.base==0 and op.mem.index==0 and op.mem.disp in imports:
                dll,name=imports[op.mem.disp]
                if name in WATCH: refs.append((op.mem.disp,dll,name,'direct'))
        if x.mnemonic in ('call','jmp') and x.operands:
            op=x.operands[0]
            if op.type==X86_OP_IMM and op.imm in thunks:
                va=thunks[op.imm]; dll,name=imports[va]
                if name in WATCH: refs.append((op.imm,dll,name,'thunk'))
        if refs:
            for ref in refs:
                hits.append((x,ref,sn))
    # print per-site context, but focus all watched; cap
    for x,ref,sn in hits:
        va,dll,name,how=ref
        if name not in {'CreateProcessW','CreateProcessA','ShellExecuteExW','ShellExecuteW','GetCommandLineW','GetCommandLineA','GetEnvironmentVariableW','GetEnvironmentVariableA','RegOpenKeyExW','RegQueryValueExW','CreateFileMappingW','OpenFileMappingW','MapViewOfFile','CreateMutexW','OpenMutexW','CreateNamedPipeW','ConnectNamedPipe','CreateFileW'}:
            continue
        out.append('-'*120)
        out.append(f'USE {x.address:#010x} RVA={x.address-base:#08x} {x.mnemonic} {x.op_str} -> {dll}!{name} IAT={va:#x} via={how} section={sn}')
        # print +/- 80 instructions, clipped by section
        idx=next((i for i,(a,b,c,z) in enumerate(allins) if z.address==x.address),None)
        if idx is not None:
            for z in [q[3] for q in allins[max(0,idx-95):min(len(allins),idx+50)]]:
                ann=''
                for op in z.operands:
                    if op.type==X86_OP_IMM:
                        s=cstr(pe,data,op.imm)
                        if s is not None: ann += ' ; '+repr(s)
                    if op.type==X86_OP_MEM and op.mem.base==0 and op.mem.index==0 and op.mem.disp in imports:
                        ann += ' ; '+imports[op.mem.disp][1]
                mark='>>' if z.address==x.address else '  '
                out.append(f'{mark}{z.address-base:08X} {z.bytes.hex():<24} {z.mnemonic:<9} {z.op_str}{ann}')
(ROOT/'_dyn_stage1'/'context_api_calls_correct.txt').write_text('\n'.join(out),encoding='utf-8')
print('wrote',ROOT/'_dyn_stage1'/'context_api_calls_correct.txt','lines',len(out))
