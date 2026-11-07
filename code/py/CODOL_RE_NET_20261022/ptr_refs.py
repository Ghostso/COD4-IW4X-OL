import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
for t in [0xC42647, 0x77EE40]:
    pat = struct.pack('<I', t); h = []; i = 0
    while True:
        i = d.find(pat, i)
        if i < 0: break
        v = B+i
        if 0x401000 <= v < 0xE5C8000+B: h.append(v)
        i += 1
    print('%#x refs: %s' % (t, [hex(x) for x in h[:20]]))
