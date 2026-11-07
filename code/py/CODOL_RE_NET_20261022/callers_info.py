import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000

def callers(t, lo=0x1000, hi=0x8A689A):
    r = []
    for i in range(lo, hi - 5):
        if d[i] == 0xE8:
            rel = struct.unpack_from("<i", d, i + 1)[0]
            if ((B + i + 5 + rel) & 0xffffffff) == t:
                r.append(B + i)
    return r

for t in [0x4E8660, 0x4E85E0]:
    print(hex(t), [hex(x) for x in callers(t)])
