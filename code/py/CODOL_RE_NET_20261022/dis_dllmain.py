import struct
from capstone import *
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read()
md=Cs(CS_ARCH_X86,CS_MODE_32)
def f2v(off): return 0x10000000 + (off - 0x400 + 0x1000)
va=0x1000149C
off=0x149C-0x1000+0x400
code=d[off:off+400]
for ins in md.disasm(code,va):
    print('  %#010x  %-24s %s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
