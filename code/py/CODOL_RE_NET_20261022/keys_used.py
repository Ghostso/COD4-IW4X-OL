d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin","rb").read()
B = 0x400000
for va in [0xDB971C, 0xDB9700, 0xDB9760, 0xDB9778, 0xDB978C, 0xDB8097]:
    o = va - B
    e = d.find(b"\x00", o)
    print("%#010x %r" % (va, d[o:e]))
