d=open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin","rb").read()
B=0x400000
base=0xE7B6400
o=base-B
for i in range(0,0x280,16):
    b=d[o+i:o+i+16]
    print("%#010x  %-47s %s" % (base+i, b.hex(" "), "".join(chr(c) if 32<=c<127 else "." for c in b)))
