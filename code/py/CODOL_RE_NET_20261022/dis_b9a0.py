import struct
from capstone import *
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
for va, n in [(0xB9A010, 0xA0), (0xB9A0D0, 0x40), (0xB9A0F0, 0x40), (0xB9A440, 0x80)]:
    print('\n===== %#x =====' % va)
    for ins in md.disasm(d[va-B:va-B+n], va):
        print('  %#010x  %-24s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
