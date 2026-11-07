import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def u32(va): return struct.unpack('<I', d[va-B:va-B+4])[0]
print('conn SM jump table @0x7F2994 (state 0..9):')
for i in range(10):
    print('  state %d -> %#010x' % (i, u32(0x7F2994+i*4)))
print()
print('DW SM jump table @0x7F2850 (state 1..4):')
for i in range(4):
    print('  state %d -> %#010x' % (i+1, u32(0x7F2850+i*4)))
