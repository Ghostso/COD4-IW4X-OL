import struct
from capstone import *
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
va=0x77EE40
code=d[va-BASE:va-BASE+0x300]
for ins in md.disasm(code,va):
    print('  %#010x  %-26s %s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
