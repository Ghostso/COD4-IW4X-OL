from pathlib import Path
import pefile
from capstone import *
fn=r'COD OL/TCLS/Client.exe'; p=pefile.PE(fn,fast_load=True); s=p.sections[1]; b=s.get_data(); base=0x400000+s.VirtualAddress
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for start,end in [(0,0x300)]:
    for ins in md.disasm(b[start:end],base+start):
        if 0x41f400 <= ins.address <= 0x41f700: print('DATA',hex(ins.address),ins.mnemonic,ins.op_str)
        if ins.mnemonic in ('call','jmp'):
            for op in ins.operands:
                if op.type==CS_OP_IMM: print(hex(ins.address),ins.mnemonic,hex(op.imm))

