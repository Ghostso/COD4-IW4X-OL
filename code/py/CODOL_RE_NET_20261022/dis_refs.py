import struct
from capstone import *
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=False
def dis(va,n=80,back=32):
    o=va-BASE-back
    code=d[o:o+n+back]
    print('=== %#010x ==='%va)
    for ins in md.disasm(code, va-back):
        print('  %#010x  %-24s %s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
for va in [0x4FD592,0x621B2E,0x77FC13,0xAD6D81,0xBB18BB]:
    dis(va,48,24)
