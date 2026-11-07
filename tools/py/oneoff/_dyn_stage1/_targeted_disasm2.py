import pefile, struct
from capstone import *
from capstone.x86 import *

def get_imports(path):
    pe=pefile.PE(path,fast_load=True); pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    out={}
    for ent in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in ent.imports:
            out[imp.address]=f'{ent.dll.decode("latin1")}!{imp.name.decode("latin1") if imp.name else "#"+str(imp.ordinal)}'
    return pe,out

def cstr(pe,va,n=220):
    try:o=pe.get_offset_from_rva(va-pe.OPTIONAL_HEADER.ImageBase)
    except:return None
    d=pe.__data__[o:o+n].split(b'\0',1)[0]
    try:s=d.decode('utf-8')
    except:
        try:s=d.decode('gbk')
        except:return None
    return s if s and all(32<=ord(c)<127 or c in '\t\r\n' for c in s) else None

def dis(path,lo,hi):
    pe,imports=get_imports(path)
    text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text')
    base=pe.OPTIONAL_HEADER.ImageBase+text.VirtualAddress
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
    print('###',path,hex(lo),hex(hi))
    for ins in md.disasm(text.get_data()[lo-base:hi-base],lo):
        notes=[]
        if ins.mnemonic in ('call','jmp') and ins.operands:
            o=ins.operands[0]
            if o.type==X86_OP_IMM: notes.append('-> '+hex(o.imm))
            elif o.type==X86_OP_MEM and o.mem.base==0 and o.mem.index==0:
                notes.append('IMP '+imports.get(o.mem.disp,'UNK@'+hex(o.mem.disp)))
        if ins.mnemonic in ('push','mov','cmp','lea'):
            for off in range(max(0,len(ins.bytes)-3)):
                v=struct.unpack_from('<I',ins.bytes,off)[0]
                s=cstr(pe,v)
                if s: notes.append('STR '+repr(s))
        print(f'{ins.address:08X}: {ins.bytes.hex():<22} {ins.mnemonic:<7} {ins.op_str}'+((' ; '+' | '.join(notes)) if notes else ''))

for p,lo,hi in [
 (r'WeGame\tgp_daemon.exe',0x4a06d0,0x4a09a0),
 (r'WeGame\tgp_daemon.exe',0x49fc80,0x4a0040),
 (r'WeGame\tgp_daemon.exe',0x4a1d80,0x4a2020),
 (r'WeGame\tgp_daemon.exe',0x494930,0x494ad0),
 (r'WeGame\client_launcher.exe',0x408e80,0x409480),
 (r'WeGame\client_launcher.exe',0x40f300,0x40f5e0),
 (r'WeGame\client_launcher.exe',0x411500,0x411820),
]:
    dis(p,lo,hi)
