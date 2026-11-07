import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va):
    o=va-B; e=d.find(b'\x00',o); return d[o:e].decode('latin1','replace')
for va in [0xDE09A8, 0xDE09B8]:
    print('%#010x %r' % (va, cstr(va)))
# dump 0xde0980..0xde0a80
o=0xDE0980-B
for i in range(0,0x100,16):
    b=d[o+i:o+i+16]
    print('%#010x  %-47s %s' % (0xDE0980+i, b.hex(' '), ''.join(chr(c) if 32<=c<127 else '.' for c in b)))