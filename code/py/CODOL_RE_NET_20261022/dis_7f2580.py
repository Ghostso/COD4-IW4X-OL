import struct
from capstone import *
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
va = 0x7F2580
for ins in md.disasm(d[va-B:va-B+0x80], va):
    print('  %#010x  %-24s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
