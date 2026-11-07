import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
for g in [0x3143770, 0x3143774, 0x3143778, 0x314377C, 0x8424360]:
    pat = struct.pack("<I", g)
    h = []
    i = 0
    while True:
        i = d.find(pat, i)
        if i < 0:
            break
        v = B + i
        if 0x401000 <= v < 0xE5C8000:
            h.append(v)
        i += 1
    print("%#010x refs=%d %s" % (g, len(h), [hex(x) for x in h[:12]]))
print()
def u32(va):
    return struct.unpack("<I", d[va-B:va-B+4])[0]
for g in [0x3143770, 0x3143774, 0x3143778, 0x314377C]:
    print("%#010x = %#010x" % (g, u32(g)))
