import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def rd(va, n=4):
    return d[va-B:va-B+n]
def u32(va):
    return struct.unpack('<I', rd(va))[0]
def cstr(va):
    o = va-B; e = d.find(b'\x00', o); return d[o:e].decode('latin1','replace')
def rtti_for_vtable(vt):
    col = u32(vt-4)
    print('vtable %#x -> COL %#x' % (vt, col))
    if not (0x400000 <= col < 0xEA59000):
        print('  COL out of image'); return
    sig, off, cd, td_rva, chd_rva = struct.unpack('<IIIII', rd(col, 20))
    print('  sig=%#x offset=%#x cd=%#x td_rva=%#x chd_rva=%#x' % (sig, off, cd, td_rva, chd_rva))
    name_va = B + td_rva + 16
    print('  type name:', cstr(name_va))
for vt in [0xD59A7C]:
    rtti_for_vtable(vt)
# also scan for other vtables nearby in .data 0xD59xxx
print('\n--- nearby vtables ---')
for vt in range(0xD59A00, 0xD59B00, 4):
    col = u32(vt-4)
    if 0x400000 <= col < 0xEA59000:
        sig = u32(col)
        if sig == 0:
            try:
                rtti_for_vtable(vt)
            except Exception as e:
                pass