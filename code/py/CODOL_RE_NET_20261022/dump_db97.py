d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
o = 0xDB96E0 - B
for i in range(0, 0xA0, 16):
    b = d[o+i:o+i+16]
    print(hex(0xDB96E0+i), b.hex(' '), ''.join(chr(c) if 32 <= c < 127 else '.' for c in b))
