import struct
from capstone import *
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
def dis(va,back=64,n=220):
    print('\n=== %#010x ==='%va)
    code=d[va-BASE-back:va-BASE+n]
    for ins in md.disasm(code,va-back):
        print('  %#010x  %-30s %s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
for va in [0x55ADA0,0x55B650,0x621B20]:
    dis(va)
