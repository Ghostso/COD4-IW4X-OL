from pathlib import Path
import pefile, struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_MEM, CS_OP_IMM

def va_to_off(pe, va):
    return pe.get_offset_from_rva(va - pe.OPTIONAL_HEADER.ImageBase)

def read_cstr(data, off, maxlen=512):
    e=data.find(b'\0',off)
    if e<0: e=min(len(data),off+maxlen)
    return data[off:e].decode('latin1',errors='replace')

def recover_function_starts(pe, data, target_vas, xref_vas):
    # Recover likely function starts by finding known prologues within a window, with
    # simple heuristics around push ebp / mov ebp,esp and aligned starts.
    starts=set()
    for va in list(target_vas)+list(xref_vas):
        rva=va-pe.OPTIONAL_HEADER.ImageBase
        s=pe.get_section_by_rva(rva)
        if not s: continue
        sb=s.VirtualAddress; se=sb+s.Misc_VirtualSize
        srva=max(sb, rva-0x4000); erva=min(se, rva+0x4000)
        base=pe.OPTIONAL_HEADER.ImageBase
        blob=s.get_data()
        for o in range(srva-sb, min(len(blob),erva-sb)-5):
            at=base+sb+o
            if blob[o:o+3] in (b'\x55\x8b\xec', b'\x6a\xff\x68', b'\x53\x56\x57', b'\x83\xec'):
                if abs(at-va)<=0x4000:
                    starts.add(at)
    return sorted(starts)

for path in [r'COD OL\WeGameLauncher\launcher.exe', r'WeGame\tgp_daemon.exe', r'WeGame\wegame.exe']:
    pe=pefile.PE(path,fast_load=True); data=Path(path).read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    iat={}
    for ent in pe.DIRECTORY_ENTRY_IMPORT:
        dll=ent.dll.decode(errors='replace')
        for imp in ent.imports:
            if imp.name:
                iat[imp.address]=(dll,imp.name.decode(errors='replace'))
    interesting_names=[i for i,v in iat.items() if any(k in v[1] for k in ('CommandLine','Environment','Process','FileMapping','Event','Mutex','Pipe','CreateProcess','ShellExecute','RegOpen','RegQuery','FindWindow','SendMessage','WaitFor'))]
    # direct xrefs as in previous script
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
    xrefs=[]
    for sec in pe.sections:
        if not (sec.Characteristics & 0x20000000): continue
        blob=sec.get_data(); va=base+sec.VirtualAddress
        for ins in md.disasm(blob,va):
            for op in ins.operands:
                if op.type==CS_OP_MEM and op.mem.base==0 and op.mem.index==0 and op.mem.disp in interesting_names:
                    xrefs.append((ins.address, op.mem.disp, ins.mnemonic, ins.op_str))
    # strings near each xref
    print('\n'+'='*110)
    print(path, 'xrels', len(xrefs))
    for xva,iatva,mnem,ops in xrefs:
        xoff=va_to_off(pe,xva)
        lo=max(0,xoff-0x100); hi=min(len(data),xoff+0x100)
        strings=[]
        for mo in re.finditer(rb'[\x20-\x7e]{4,}',data[lo:hi]):
            s=mo.group().decode('latin1')
            strings.append((lo+mo.start(),s))
        print(f'\n{path} XREF {xva:08X} {mnem} {ops} IAT={iatva:08X}:{iat[iatva][0]}!{iat[iatva][1]}')
        for o,s in strings:
            print(f'  STR {o:08X} {s}')
