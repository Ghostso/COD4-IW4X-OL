import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va):
    o=va-B; e=d.find(b'\x00',o); return d[o:e].decode('latin1','replace')
def u32(va): return struct.unpack('<I', d[va-B:va-B+4])[0]
def u16(va): return struct.unpack('<H', d[va-B:va-B+2])[0]
print('--- runtime auth/lsg globals in dump ---')
for va in [0x81A76A8, 0x81A7F34, 0x81A9780, 0x81A9EC4, 0x81A9EB8, 0x81A56A4, 0x81A76E4]:
    print('  %#010x = %#010x  str=%r' % (va, u32(va), cstr(va)[:60]))
print('  0x81A9780 u16 =', u16(0x81A9780))
print('  0x81A9EC4 u16 =', u16(0x81A9EC4))
print()
print('--- 0x331C5C0 flag ---', hex(u32(0x331C5C0)))
print('--- dw states ---')
for va in [0x84ABA50,0x84ABA54,0x84ABA5C,0x84ABA60,0x84ABA78,0x84ABA4C,0x849BA3D,0x849B874]:
    print('  %#010x = %#010x' % (va, u32(va)))
print('--- objects ---')
for va in [0x84ABB08,0x84ABB14,0x84ABB10]:
    print('  %#010x = %#010x' % (va, u32(va)))
