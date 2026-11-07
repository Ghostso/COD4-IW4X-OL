import struct
from capstone import *
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read()
md=Cs(CS_ARCH_X86,CS_MODE_32)
# file->rva: .text raw 0x400 va 0x1000
def f2v(off): return 0x10000000 + (off - 0x400 + 0x1000)
va=f2v(0x27D80C)
print('patch VA',hex(va))
code=d[0x27D80C-0x80:0x27D80C+0x80]
for ins in md.disasm(code, va-0x80):
    mark='  <<<' if ins.address==va else ''
    print('  %#010x  %-24s %s %s%s'%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,mark))
print('\nbytes around patch orig:',d[0x27D80C:0x27D80C+16].hex())
