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
for t in [0x7F26C0, 0x7F2600, 0x77FFB0, 0x7EE9D0, 0x7EE9B0]:
    print('%#010x <- %s' % (t, [hex(x) for x in callers(t)]))
