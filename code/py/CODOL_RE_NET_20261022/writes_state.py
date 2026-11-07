import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
pat = struct.pack('<I', 0x84ABA60)
hits = []
i = 0
while True:
    i = d.find(pat, i)
    if i < 0: break
    v = B + i
    if 0x401000 <= v < 0xE5C8000:
        hits.append((v, d[i-4:i+8]))
    i += 1
print('refs to 0x84ABA60:', len(hits))
for v, ctx in hits:
    print('  %#010x  prev=%s  next=%s' % (v, ctx[:4].hex(' '), ctx[4:8].hex(' ')))
