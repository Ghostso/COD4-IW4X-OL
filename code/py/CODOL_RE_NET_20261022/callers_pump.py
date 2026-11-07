import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def callers(t, lo=0x1000, hi=0x8A689A):
    r = []
    for i in range(lo, min(hi, len(d))-5):
        if d[i] == 0xE8:
            rel = struct.unpack_from('<i', d, i+1)[0]
            if ((B+i+5+rel) & 0xffffffff) == t:
                r.append(B+i)
    return r
for t in [0x7F28F0, 0x7F2AB0, 0x7F29C0, 0x7F3100, 0x7F3190, 0x7F2DB0]:
    print('%#010x <- %s' % (t, [hex(x) for x in callers(t)]))
print('\nIAT slots:')
for slot in [0xCA8158, 0xCA8150, 0xCA8104, 0xCA80FC, 0xCA8100]:
    print('  %#x = %#010x' % (slot, struct.unpack('<I', d[slot-B:slot-B+4])[0]))
print('\nstrings near 0xDC6EC0:')
o = 0xDC6EC0-B
import re
print(repr(d[o:o+120]))