import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va,n=200):
    o=va-B
    e=d.find(b'\x00',o,o+n)
    return d[o:e]
for va in [0xE3EC988, 0xE3EC980, 0xE3ECA10, 0xE3EC578, 0x3269854]:
    try: print('%#010x %r' % (va, cstr(va)[:160]))
    except Exception as e: print(va, e)
# what is at 0x8269854 -> pointer
def u32(va): return struct.unpack('<I', d[va-B:va-B+4])[0]
print('0x8269854 ->', hex(u32(0x8269854)))
