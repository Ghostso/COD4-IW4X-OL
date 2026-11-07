import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def u32(va): return struct.unpack('<I', d[va-B:va-B+4])[0]
print('jump table 0x7F2850 (states 1..4):')
for i, va in enumerate(range(0x7F2850, 0x7F2860, 4)):
    print('  idx %d -> %#010x' % (i+1, u32(va)))
print()
print('state 0x84ABA50 =', u32(0x84ABA50))
print('state 0x84ABA5C =', u32(0x84ABA5C))
print('pump idx 0x849BA30 =', u32(0x849BA30), ' dwState 0x849BA34 =', u32(0x849BA34))
