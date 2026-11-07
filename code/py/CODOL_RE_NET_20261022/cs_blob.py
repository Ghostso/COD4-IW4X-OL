import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
base = 0x0C47A48D
o = base - B
print('base', hex(base), 'offset', hex(o))
parts = d[o:o+420].split(b'\x00')
for i, p in enumerate(parts[:14]):
    print(i, repr(p[:100]))
