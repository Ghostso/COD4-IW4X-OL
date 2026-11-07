d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
import struct
def u32(va): return struct.unpack('<I', d[va-B:va-B+4])[0]
def u16(va): return struct.unpack('<H', d[va-B:va-B+2])[0]
def dump(va, n=64):
    o=va-B; b=d[o:o+n]
    print('  %#010x  %s  %s' % (va, b.hex(' '), ''.join(chr(c) if 32<=c<127 else '.' for c in b)))
for va in [0x331C5C4, 0x331C5D8, 0x331C65C, 0x331C658, 0x331C670, 0x331CAF8]:
    print('%#x u32=%#x u16=%#x' % (va, u32(va), u16(va)))
    dump(va)
