import struct
from capstone import *
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
def dis(va,back=0,n=240):
    print('=== %#010x ==='%va)
    code=d[va-BASE-back:va-BASE+n]
    for ins in md.disasm(code,va-back):
        print('  %#010x  %-28s %s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
dis(0xE5DC690,0,320)
print('--- refs to import thunk 0xE5DC665 ---')
pat=struct.pack('<I',0xE5DC665)
i=0
while True:
    i=d.find(pat,i)
    if i<0: break
    print('  %#x ctx=%s'%(BASE+i,d[i-8:i+8].hex()))
    i+=1
