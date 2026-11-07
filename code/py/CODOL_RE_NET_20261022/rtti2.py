import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va,n=120):
    o=va-B; e=d.find(b'\x00',o,o+n); return d[o:e].decode('latin1','replace')
# RTTI: vtable 0xd5a1f8 -> COL
def u32(va): return struct.unpack('<I', d[va-B:va-B+4])[0]
for vt in [0xd5a1f8, 0xd59a7c, 0xd5a0f8]:
    col = u32(vt-4)
    print('vtable %#x COL %#x' % (vt, col))
    if 0x400000 <= col < 0xEA59000:
        sig,off,cd,td,chd = struct.unpack('<IIIII', d[col-B:col-B+20])
        print('   sig=%#x off=%#x td=%#x chd=%#x' % (sig,off,td,chd))
        # type descriptor: td points to ??_R0?AV...  then name at td+8
        for delta in (8,12,16,20):
            o=B+td+delta
            s=d[o:o+120].split(b'\x00')[0]
            print('    td+%d %r' % (delta, s[:100]))
