from pathlib import Path
import pefile, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
p=Path(r'WeGame/tgp_daemon.exe')
pe=pefile.PE(str(p),fast_load=True)
data=p.read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
terms=[b'StartFor',b'AddPath',b'cmd_launcher_info.ini',b'client_launcher.exe']
for term in terms:
    off=data.find(term)
    if off<0: continue
    rva=pe.get_rva_from_offset(off); va=base+rva
    ptr=struct.pack('<I',va)
    refs=[]; start=0
    while True:
        i=data.find(ptr,start)
        if i<0: break
        refs.append(i); start=i+1
    print('\n'+'='*100)
    print(term.decode(), 'string', hex(off), hex(rva), hex(va), 'refs', [hex(x) for x in refs])
    for roff in refs:
        rrva=pe.get_rva_from_offset(roff)
        sec=pe.get_section_by_offset(roff)
        print('\nREF',hex(roff),'RVA',hex(rrva),'section',sec.Name if sec else None)
        lo=max(0,roff-96); hi=min(len(data),roff+128)
        for ins in md.disasm(data[lo:hi],base+pe.get_rva_from_offset(lo)):
            mark='>>' if ins.address==base+rrva else '  '
            print(mark,f'{ins.address-base:08X}',ins.bytes.hex().ljust(24),ins.mnemonic,ins.op_str)
