import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va):
    o=va-B; e=d.find(b'\x00',o); return d[o:e].decode('latin1','replace')
for lo,hi,name in [(0x7F2DB0,0x7F3100,'0x7F2DB0'),(0x7F3100,0x7F3190,'0x7F3100'),(0x7F3190,0x7F3400,'0x7F3190')]:
    print('\n== %s ==' % name)
    o=lo-B
    for i in range(o, hi-B-5):
        if d[i]==0x68:
            t=struct.unpack_from('<I',d,i+1)[0]
            if 0xD40000 <= t < 0xDF0000:
                s=cstr(t)
                if s and len(s)>2: print('  %#010x push %#010x %r' % (B+i, t, s[:110]))
