import struct
p = r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin"
d = open(p, "rb").read()
B = 0x400000

def callers(t):
    r = []
    for i in range(0x1000, 0x8A6890):
        if d[i] == 0xE8:
            rel = struct.unpack_from("<i", d, i+1)[0]
            if ((B+i+5+rel) & 0xffffffff) == t:
                r.append(B+i)
    return r

for t in (0x77FBF0, 0x77FCD0, 0x77FF38, 0x5C0F50, 0x5C0FD0, 0x756D00):
    print(hex(t), [hex(x) for x in callers(t)])
