import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va, n=200):
    o=va-B
    e=d.find(b'\x00',o,o+n)
    return d[o:e]
for va in [0xCC383C, 0xD5A33C, 0xD5A228, 0xD5A114, 0xDB7AC0, 0xD59AEC, 0xD5A2CC]:
    print('%#010x len=%d %r' % (va, len(cstr(va)), cstr(va)))
# dump around 0xCC3830
o=0xCC3830-B
for i in range(0,0x60,16):
    b=d[o+i:o+i+16]
    print('%#010x  %-47s %s' % (0xCC3830+i, b.hex(' '), ''.join(chr(c) if 32<=c<127 else '.' for c in b)))
