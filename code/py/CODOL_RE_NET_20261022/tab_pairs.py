import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
o = 0x32AD060 - B
pairs = []
for i in range(12):
    a = struct.unpack_from("<I", d, o + 8 + i * 8)[0]
    b = struct.unpack_from("<I", d, o + 0xC + i * 8)[0]
    sa = d[a-B:d.find(b"\x00", a-B)].decode("latin1", "replace")
    sb = d[b-B:d.find(b"\x00", b-B)].decode("latin1", "replace")
    pairs.append((sa, sb))
print("pairs", len(pairs))
for k, v in pairs:
    print("  %-20s = %r" % (k, v))
