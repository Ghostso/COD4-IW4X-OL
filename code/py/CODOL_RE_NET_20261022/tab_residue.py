import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
o = 0x32AD060 - B
names = [struct.unpack_from("<I", d, o + 8 + i * 8)[0] for i in range(64)]
vals = [struct.unpack_from("<I", d, o + 0xC + i * 8)[0] for i in range(64)]
print("name ptrs nonzero", sum(1 for v in names if v))
print("value ptrs nonzero", sum(1 for v in vals if v))
for i in range(8):
    a, b = names[i], vals[i]
    sa = d[a-B:d.find(b"\x00", a-B)].decode("latin1", "replace") if a else ""
    sb = d[b-B:d.find(b"\x00", b-B)].decode("latin1", "replace") if b else ""
    print(i, hex(a), repr(sa), hex(b), repr(sb))
seg = d[o+0x20C:o+0x30C]
print("text:", "".join(chr(c) if 32 <= c < 127 else "." for c in seg))
