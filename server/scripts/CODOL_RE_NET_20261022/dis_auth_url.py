import struct
from capstone import *
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
# find function start containing 0xB9AC89
target = 0xB9AC89
o = target-B
for k in range(0x600):
    if d[o-k]==0x55 and d[o-k+1]==0x8B and d[o-k+2]==0xEC:
        start = B+o-k; break
print('func start', hex(start))
for ins in md.disasm(d[start-B:start-B+0x300], start):
    print('%#010x  %-26s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
