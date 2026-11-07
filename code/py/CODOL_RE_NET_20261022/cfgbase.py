import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
for g in [0x32AD060, 0x32AF42C, 0x32A73C4, 0x331C0C8]:
    pat = struct.pack('<I', g); h=[]; i=0
    while True:
        i = d.find(pat, i)
        if i < 0: break
        v = B+i
        if 0x401000 <= v < 0xE5C8000: h.append(v)
        i += 1
    print('%#010x refs=%d %s' % (g, len(h), [hex(x) for x in h[:16]]))
