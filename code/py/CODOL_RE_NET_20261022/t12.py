import struct
p = r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin"
d = open(p, "rb").read()
B = 0x400000
out = []
for i in range(21):
    o = 0x614D94 - B + i * 4
    out.append(hex(struct.unpack_from("<I", d[o:o+4])[0]))
print(" | ".join(out))
