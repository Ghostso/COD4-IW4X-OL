import pefile, struct
from capstone import *
from capstone.x86 import *

def ctx(path,lo,hi):
    pe=pefile.PE(path,fast_load=True); pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    imports={}
    for ent in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in ent.imports: imports[pe.OPTIONAL_HEADER.ImageBase+imp.address]=ent.dll.decode('latin1')+'!'+((imp.name or b'#').decode('latin1') if imp.name else '#'+str(imp.ordinal))
    text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text')
    base=pe.OPTIONAL_HEADER.ImageBase+text.VirtualAddress; data=text.get_data()
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
    print('\n'+'='*100+f'\n{path} {lo:08X}-{hi:08X}')
    for ins in md.disasm(data[lo-base:hi-base],lo):
        notes=[]
        if ins.mnemonic in ('call','jmp') and ins.operands:
            o=ins.operands[0]
            if o.type==X86_OP_IMM: notes.append('-> '+hex(o.imm))
            elif o.type==X86_OP_MEM and o.mem.base==0 and o.mem.index==0:
                notes.append('IMP '+imports.get(o.mem.disp,'UNK@'+hex(o.mem.disp)))
        if len(ins.bytes)>6 and ins.mnemonic in ('push','mov','cmp'):
            for off in range(len(ins.bytes)-3):
                v=struct.unpack_from('<I',ins.bytes,off)[0]
                try:
                    o=pe.get_offset_from_rva(v-pe.OPTIONAL_HEADER.ImageBase)
                    d=pe.__data__[o:o+160].split(b'\0',1)[0]
                    if len(d)>=3 and all(32<=x<127 or x in (9,10,13) for x in d): notes.append('STR? '+repr(d.decode('latin1')))
                except: pass
        print(f'{ins.address:08X}: {ins.bytes.hex():<22} {ins.mnemonic:<7} {ins.op_str}' + ((' ; '+' | '.join(notes)) if notes else ''))

ctx(r'WeGame\tgp_daemon.exe',0x4a07c0,0x4a0980)
ctx(r'WeGame\tgp_daemon.exe',0x4a2420,0x4a2690)
ctx(r'WeGame\tgp_daemon.exe',0x4a1d80,0x4a2020)
ctx(r'WeGame\client_launcher.exe',0x409180,0x409490)
ctx(r'WeGame\client_launcher.exe',0x408b30,0x408da0)
ctx(r'WeGame\client_launcher.exe',0x411500,0x411820)
