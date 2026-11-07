d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
o=0xDE08C0-B
for i in range(0,0x90,16):
    b=d[o+i:o+i+16]
    print('%#010x  %-47s %s' % (0xDE08C0+i, b.hex(' '), ''.join(chr(c) if 32<=c<127 else '.' for c in b)))
