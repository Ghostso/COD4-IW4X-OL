import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def refs(g):
    pat = struct.pack('<I', g); h=[]; i=0
    while True:
        i = d.find(pat, i)
        if i < 0: break
        v = B+i
        if 0x401000 <= v < 0xE5C8000: h.append(v)
        i += 1
    return h
for g in [0x331C5C0, 0x331C5C4, 0x331C5D8, 0x331C65C, 0x331C670]:
    r = refs(g)
    print('%#010x refs=%d %s' % (g, len(r), [hex(x) for x in r[:10]]))
