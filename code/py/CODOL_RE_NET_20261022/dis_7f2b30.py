import struct
from capstone import *
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
for va, n in [(0x7F2B30, 0x60), (0xB992E0, 0x140)]:
    print('\n===== %#x =====' % va)
    for ins in md.disasm(d[va-B:va-B+n], va):
        print('  %#010x  %-26s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
