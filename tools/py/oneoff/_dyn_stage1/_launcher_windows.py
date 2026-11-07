from pathlib import Path
import pefile, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
path=r'COD OL\WeGameLauncher\launcher.exe'
pe=pefile.PE(path,fast_load=True); data=Path(path).read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase
md=Cs(CS_ARCH_X86,CS_MODE_32)
for va in [0x42ADB5,0x42AE9D,0x42B617,0x42B63B,0x42F792,0x42F861,0x42F897,0x420AB0,0x42286C,0x42290F,0x427FBA,0x428020,0x432402,0x447F53,0x447F6A]:
    rva=va-base
    s=pe.get_section_by_rva(rva)
    if not s: continue
    blob=s.get_data(); start=max(s.VirtualAddress, rva-0x90); end=min(s.VirtualAddress+len(blob), rva+0xa0)
    print('\n'+'='*100); print('XREF',hex(va),s.Name)
    for ins in md.disasm(blob[start-s.VirtualAddress:end-s.VirtualAddress], base+start):
        mark='>>' if ins.address==va else '  '
        print(mark,f'{ins.address-base:08X}',ins.mnemonic,ins.op_str)
