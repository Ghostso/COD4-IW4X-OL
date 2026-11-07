import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
def refs(va):
    pat = struct.pack("<I", va)
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
    return h
for va in [0xDBFE28, 0xDC6628, 0xDBFF0C, 0xDBFF58]:
    print(hex(va), refs(va)[:12])
