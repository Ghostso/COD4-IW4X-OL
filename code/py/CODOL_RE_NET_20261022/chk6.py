import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
base = 0x2FAFE10
for idx in (0, 1, 2, 5, 6, 7, 8, 765):
    o = base - B + idx * 0x400
    print(idx, repr(d[o:o+100].split(b"\x00")[0]))
