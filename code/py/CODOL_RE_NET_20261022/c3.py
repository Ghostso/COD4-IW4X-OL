import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
base = 0x3306994
pat = struct.pack("<I", base)
out = []
i = 0
while True:
    i = d.find(pat, i)
    if i < 0:
        break
    v = B + i
    if 0x401000 <= v < 0xE5C8000:
        out.append(v)
    i += 1
print("total", len(out))
for v in out:
    print(hex(v), d[v-B-8:v-B+8].hex(" "))
