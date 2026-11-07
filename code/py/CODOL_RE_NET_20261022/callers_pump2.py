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
for t in [0x7F26E0, 0x7F2700, 0x7F25B0]:
    print('%#010x <- %s' % (t, [hex(x) for x in callers(t)]))
# find function start at 0x7f26e0 area
def funcstart(va, limit=0x300):
    o=va-B
    for k in range(limit):
        if d[o-k]==0x55 and d[o-k+1]==0x8B and d[o-k+2]==0xEC:
            return B+o-k
    return None
for va in [0x7F26E0, 0x7F271B]:
    fs=funcstart(va)
    print('funcstart for %#x = %s, callers=%s' % (va, hex(fs) if fs else None, [hex(x) for x in callers(fs)] if fs else None))