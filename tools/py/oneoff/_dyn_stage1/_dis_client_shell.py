from pathlib import Path
import pefile
from capstone import *
fn=r'COD OL/TCLS/Client.exe'
p=pefile.PE(fn,fast_load=True); s=p.sections[0]; b=s.get_data(); base=0x400000+s.VirtualAddress
md=Cs(CS_ARCH_X86,CS_MODE_32)
for start,end in [(0,0x200),(0x200,0x700),(0x1000,0x1400),(0x1d00,0x2300)]:
    print('---',hex(start))
    for ins in md.disasm(b[start:end],base+start): print(f'{ins.address:08x} {ins.bytes.hex():<18} {ins.mnemonic} {ins.op_str}')

