import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
va = 0xC87A48D
print('configstring blob VA =', hex(va))
pat = struct.pack('<I', va)
h = []
i = 0
while True:
    i = d.find(pat, i)
    if i < 0:
        break
    v = B + i
    if 0x401000 <= v < 0x0E5C8000:
        h.append(v)
    i += 1
print('pointers to blob:', len(h), [hex(x) for x in h[:20]])
o = va - B
print('--- 96 bytes before ---')
print(d[o-96:o].hex(' '))
for k in range(1, 9):
    print('  -%d*4: %#010x' % (k, struct.unpack('<I', d[o-4*k:o-4*k+4])[0]))
