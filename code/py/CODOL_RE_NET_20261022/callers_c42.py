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
def funcstart(va, limit=0x300):
    o = va - B
    for k in range(limit):
        if d[o-k] == 0x55 and d[o-k+1] == 0x8B and d[o-k+2] == 0xEC:
            return B+o-k
    return None
fs = funcstart(0xC42783)
print('call site 0xC42783 funcstart', hex(fs) if fs else None)
if fs:
    print('  callers of funcstart:', [hex(x) for x in callers(fs)])
