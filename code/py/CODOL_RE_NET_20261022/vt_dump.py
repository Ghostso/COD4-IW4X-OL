import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def u32(va): return struct.unpack('<I', d[va-B:va-B+4])[0]
for va in range(0xD59A60, 0xD59AB0, 4):
    print('%#010x: %#010x' % (va, u32(va)))