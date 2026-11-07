import pefile, struct, re
from capstone import *
from capstone.x86 import *

def load(path):
    pe=pefile.PE(path,fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    import_at={}
    for ent in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in ent.imports:
            import_at[pe.OPTIONAL_HEADER.ImageBase+imp.address]=f'{ent.dll.decode("latin1")}!{imp.name.decode("latin1") if imp.name else "#"+str(imp.ordinal)}'
    return pe,import_at

def file_bytes(pe):
    text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text')
    return text.get_data(),pe.OPTIONAL_HEADER.ImageBase+text.VirtualAddress

def va_off(pe,va):
    try:return pe.get_offset_from_rva(va-pe.OPTIONAL_HEADER.ImageBase)
    except:return None

def cstr(pe,va,maxn=160):
    o=va_off(pe,va)
    if o is None:return None
    d=pe.__data__[o:o+maxn]
    if b'\0' not in d:return None
    d=d.split(b'\0',1)[0]
    try:s=d.decode('utf-8')
    except:
        try:s=d.decode('gbk')
        except:return None
    if sum(ch.isprintable() or ch in '\r\n\t' for ch in s)/max(len(s),1) < .85:return None
    return s

def dis(path,start,end):
    pe,imports=load(path); text,base=file_bytes(pe)
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
    print('\n'+'='*100);print(path,hex(start),hex(end))
    last=None
    for ins in md.disasm(text[start-base:end-base],start):
        refs=[]
        if ins.mnemonic in ('call','jmp'):
            if ins.operands and ins.operands[0].type==X86_OP_IMM:
                t=ins.operands[0].imm
                refs.append('-> '+hex(t))
            elif ins.operands and ins.operands[0].type==X86_OP_MEM:
                m=ins.operands[0].mem
                if m.base==0 and m.index==0:
                    if m.disp in imports:refs.append('IMP '+imports[m.disp])
                    else:refs.append('MEM '+hex(m.disp))
        for op in ins.operands:
            if op.type==X86_OP_IMM:
                v=op.imm & 0xffffffff
                s=cstr(pe,v)
                if s:refs.append('STR '+repr(s[:100])+' @'+hex(v))
        tag=(' ; '+' | '.join(refs)) if refs else ''
        print(f'{ins.address:08X}: {ins.bytes.hex():<24} {ins.mnemonic:<7} {ins.op_str}{tag}')

for args in [
 (r'WeGame\tgp_daemon.exe',0x4a0700,0x4a0c20),
 (r'WeGame\tgp_daemon.exe',0x4a23d0,0x4a2660),
 (r'WeGame\client_launcher.exe',0x408b00,0x409480),
 (r'WeGame\client_launcher.exe',0x40f300,0x40f5a0),
 (r'WeGame\client_launcher.exe',0x4114c0,0x411830),
]:dis(*args)
