import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin","rb").read()
B = 0x400000
pat = struct.pack("<I", 0x32AD060)
out = []
i = 0
while True:
    i = d.find(pat, i)
    if i < 0:
        break
    out.append(B + i)
    i += 1
print("refs", len(out))
for v in out:
    print(hex(v), d[v-B-6:v-B+10].hex(" "))
