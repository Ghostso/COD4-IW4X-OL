from pathlib import Path
import pefile, struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_MEM, CS_OP_IMM

ROOT = Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
OUT = ROOT / r'_dyn_stage1\stage2_focus.txt'

def parse_pe(path):
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    data = path.read_bytes()
    base = pe.OPTIONAL_HEADER.ImageBase
    imports = {}
    if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
        for ent in pe.DIRECTORY_ENTRY_IMPORT:
            dll = ent.dll.decode('ascii', 'replace')
            for imp in ent.imports:
                name = imp.name.decode('ascii', 'replace') if imp.name else '#%d' % imp.ordinal
                imports[imp.address] = (dll, name)
    return pe, data, base, imports

def sec_for_rva(pe, rva):
    for sec in pe.sections:
        end = sec.VirtualAddress + max(sec.Misc_VirtualSize, sec.SizeOfRawData)
        if sec.VirtualAddress <= rva < end:
            return sec
    return None

def disasm_region(pe, base, imports, lo, hi, out, title):
    out.write('\n' + '='*120 + '\n')
    out.write(title + '\n')
    sec = sec_for_rva(pe, lo-base)
    if sec is None:
        out.write('NO_SECTION\n')
        return
    blob = sec.get_data()
    sva = base + sec.VirtualAddress
    start = max(lo, sva)
    end = min(hi, sva + len(blob))
    code = blob[start-sva:end-sva]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for ins in md.disasm(code, start):
        notes=[]
        for op in ins.operands:
            if op.type == CS_OP_MEM and op.mem.base == 0 and op.mem.index == 0 and op.mem.disp in imports:
                dll,nm=imports[op.mem.disp]
                notes.append('IMPORT %s!%s' % (dll,nm))
            if op.type == CS_OP_IMM and (start <= op.imm < end or 0x400000 <= op.imm < 0x700000):
                notes.append('IMMVA=%08X' % op.imm)
        note = (' ; ' + '; '.join(notes)) if notes else ''
        out.write('%08X %-24s %-8s %s%s\n' % (ins.address-base, ins.bytes.hex(), ins.mnemonic, ins.op_str, note))

def list_import_xrefs(pe, base, imports, out, title, filter_names=None):
    out.write('\n' + '='*120 + '\n' + title + '\n')
    targets = {a:v for a,v in imports.items() if filter_names is None or v[1] in filter_names}
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
    hits=[]
    for sec in pe.sections:
        if not (sec.Characteristics & 0x20000000):
            continue
        blob=sec.get_data(); va=base+sec.VirtualAddress
        for ins in md.disasm(blob, va):
            for op in ins.operands:
                if op.type == CS_OP_MEM and op.mem.base == 0 and op.mem.index == 0 and op.mem.disp in targets:
                    hits.append((ins.address, targets[op.mem.disp], ins.mnemonic, ins.op_str))
    for a,(dll,n),mn,ops in sorted(hits):
        out.write('%08X %-8s %-45s -> %s!%s\n' % (a-base,mn,ops,dll,n))

def find_ascii_strings(data):
    return [(m.start(),m.group().decode('latin1')) for m in re.finditer(rb'[\x20-\x7e]{4,}',data)]

def find_utf16_strings(data):
    out=[]
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00){4,}',data):
        try:s=m.group().decode('utf-16le')
        except:continue
        out.append((m.start(),s))
    return out

def ptr_refs(pe, data, va):
    refs=[]
    for sec in pe.sections:
        blob=sec.get_data(); sva=pe.OPTIONAL_HEADER.ImageBase+sec.VirtualAddress
        pat=struct.pack('<I',va)
        p=0
        while True:
            i=blob.find(pat,p)
            if i<0: break
            refs.append(sva+i); p=i+1
    return refs

launcher = ROOT / r'COD OL\WeGameLauncher\launcher.exe'
with OUT.open('w',encoding='utf-8') as out:
    pe,data,base,imports = parse_pe(launcher)
    out.write('LAUNCHER %s base=%08X entry=%08X\n' % (launcher,base,pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    out.write('Interesting imports:\n')
    for a,(dll,n) in sorted(imports.items()):
        if any(k in n for k in ['Process','Thread','Event','Mutex','Mapping','CommandLine','Environment','Pipe','FindWindow','SendMessage','CreateProcess','ShellExecute','Toolhelp','Module32','RegOpen','RegQuery','WaitFor','OpenProcess','TerminateProcess']):
            out.write('%08X %s!%s\n' % (a,dll,n))
    list_import_xrefs(pe,base,imports,out,'LAUNCHER API XREFS',
        {'GetCommandLineW','CommandLineToArgvW','GetEnvironmentVariableW','CreateFileMappingW','CreateFileMappingA','OpenFileMappingA','CreateProcessW','ShellExecuteExW','CreateMutexA','OpenEventA','OpenEventW','CreateEventA','CreateEventW','WaitForSingleObject','Process32FirstW','Process32NextW','CreateToolhelp32Snapshot','Module32FirstW','OpenProcess','TerminateProcess','PeekNamedPipe','WaitForMultipleObjects'})
    disasm_region(pe,base,imports,0x412650,0x412c20,out,'LAUNCHER LIVENESS / STATE BRANCH 0x412650..0x412C20')
    disasm_region(pe,base,imports,0x412ec0,0x413380,out,'LAUNCHER ZOMBIE PATH 0x412EC0..0x413380')
    out.write('\nSTATE-related strings and refs:\n')
    keys=['wegame is running','wegame is not running','no zombie','found zombie','launch tcls','Try launch tcls','OnInstanceNotify','ProcessStateMachine']
    for off,s in sorted(find_ascii_strings(data)+find_utf16_strings(data)):
        if any(k.lower() in s.lower() for k in keys):
            try: va=base+pe.get_rva_from_offset(off)
            except: continue
            refs=ptr_refs(pe,data,va)
            out.write('%08X off=%08X refs=%s STR=%r\n' % (va,off,[hex(x) for x in refs],s))

    for relpath in [r'COD OL\codoMP_client_shipRetail.exe',r'COD OL\codoMP_client_shipRetailBase.dll']:
        path=ROOT/relpath
        pe,data,base,imports=parse_pe(path)
        out.write('\n'+'#'*140+'\nFILE %s base=%08X entry=%08X\n' % (path,base,pe.OPTIONAL_HEADER.AddressOfEntryPoint))
        list_import_xrefs(pe,base,imports,out,'IMPORT XREFS',{'GetCommandLineA','GetCommandLineW','CommandLineToArgvW','GetEnvironmentVariableA','GetEnvironmentVariableW','CreateFileMappingA','CreateFileMappingW','OpenFileMappingA','OpenFileMappingW','MapViewOfFile','CreateMutexA','CreateMutexW','OpenMutexA','OpenMutexW','CreateEventA','CreateEventW','OpenEventA','OpenEventW','CreateNamedPipeA','CreateNamedPipeW','ConnectNamedPipe','WaitNamedPipeA','WaitNamedPipeW','CreateProcessA','CreateProcessW','LoadLibraryA','LoadLibraryW'})
        terms=['WIN_NO_TCLS','IsTCLSLogOn','${CODO_TCLS_ZONE}','TCLS_SHAREDMEMEMORY','TCLS_TASMEMORY_','tcls_core','TP3GameGuardShareMapping','-src=tgp','-q','-qa']
        for off,s in sorted(find_ascii_strings(data)+find_utf16_strings(data)):
            if any(t.lower() in s.lower() for t in terms):
                try: va=base+pe.get_rva_from_offset(off)
                except: continue
                refs=ptr_refs(pe,data,va)
                out.write('STR %08X off=%08X refs=%s %r\n' % (va,off,[hex(x) for x in refs],s))
                for r in refs[:12]:
                    lo=max(base+0x1000,r-0xc0); hi=min(base+pe.OPTIONAL_HEADER.SizeOfImage,r+0x100)
                    disasm_region(pe,base,imports,lo,hi,out,'NEAR STR REF %08X' % r)
print(OUT)
