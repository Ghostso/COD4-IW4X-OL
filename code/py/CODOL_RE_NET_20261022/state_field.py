import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
# refs to [esi+0x14] style: search for the literal offset in the connection class methods range 0xB88000..0xBA0000
import re
def hits(lo,hi,pat):
    r=[]
    for i in range(lo-B, hi-B):
        if d[i:i+len(pat)]==pat: r.append(B+i)
    return r
print('+0x14 (state) writes in 0xB88xxx..0xB99xxx:')
for i in range(0xB88000-B, 0xB9A000-B-8):
    if d[i]==0xC7 and d[i+1] in (0x46,0x86) and d[i+2]==0x14:
        print('  %#010x  %s' % (B+i, d[i:i+10].hex(' ')))
