import struct
d = open("run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin", "rb").read()
B = 0x400000
def cstr(va):
    o = va - B
    e = d.find(b"\x00", o)
    return d[o:e].decode("latin1", "replace")
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
for va in [0xD90B4C, 0xD90BE8, 0xD90D0C, 0xD950F8, 0xDC5C80, 0xDC5CA0, 0xDC5CC0, 0xDC5CE0, 0xDC5CFC]:
    print(hex(va), cstr(va), [hex(x) for x in refs(va)[:10]])
