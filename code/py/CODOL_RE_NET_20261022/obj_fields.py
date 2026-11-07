import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def u32(va): return struct.unpack('<I', d[va-B:va-B+4])[0]
print('vtable of conn object (0x39f13138):')
vt = u32(0x39f13138)
print('  vt = %#010x' % vt)
for i in range(0, 0x40, 4):
    print('   [+%02x] %#010x' % (i, u32(vt+i)))
print()
print('  field [obj+0x14] = %#010x' % u32(0x39f13138+0x14))
print('  field [obj+0x160] = %#010x' % u32(0x39f13138+0x160))
print('  field [obj+0x3190] = %#010x' % u32(0x39f13138+0x3190))
print('  field [obj+0x35f4] = %#010x' % u32(0x39f13138+0x35f4))
print('  field [obj+0x35f8] u16 = %#06x' % struct.unpack('<H', d[0x39f13138+0x35f8-B:0x39f13138+0x35fa-B])[0])
print('  field [obj+0x3654] = %#010x' % u32(0x39f13138+0x3654))
print('  field [obj+0x3e58] = %#010x' % u32(0x39f13138+0x3e58))
