import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
hits = []
for i in range(0x1000, 0x8A6890 - 16):
    if d[i] == 0x68 and struct.unpack_from("<I", d, i+1)[0] == 0x2FD:
        hits.append(B+i)
print("push765", len(hits))
for h in hits[:30]:
    print(hex(h))
