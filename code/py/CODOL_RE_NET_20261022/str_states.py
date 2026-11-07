d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va):
    o=va-B; e=d.find(b'\x00',o); return d[o:e].decode('latin1','replace')
for va in [0xDE08C8,0xDE08D8,0xDE08E8,0xDE08F8,0xDE0908,0xDE0918,0xDE0928,0xDE0938,0xDE094C,0xDE096C]:
    print('%#010x %r' % (va, cstr(va)[:120]))
