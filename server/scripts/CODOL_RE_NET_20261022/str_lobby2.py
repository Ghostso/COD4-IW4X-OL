import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va):
    o=va-B; e=d.find(b'\x00',o); return d[o:e].decode('latin1','replace')
for va in [0xDC9CA4, 0xDE09B8, 0xDC9F64, 0xDC09AC, 0xDC09B8]:
    print('%#010x %r' % (va, cstr(va)))