import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va,n=120):
    o=va-B; e=d.find(b'\x00',o,o+n); return d[o:e]
o=0xDE0900-B
for i in range(0,0x60,16):
    b=d[o+i:o+i+16]
    print('%#010x  %-47s %s' % (0xDE0900+i, b.hex(' '), ''.join(chr(c) if 32<=c<127 else '.' for c in b)))
print()
for va in [0xDE08F8,0xDE090C,0xDE0920,0xDE0938]:
    print('%#010x %r' % (va, cstr(va)))
