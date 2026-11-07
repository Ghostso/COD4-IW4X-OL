import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va):
    o=va-B; e=d.find(b'\x00',o); return d[o:e].decode('latin1','replace')
for va in [0xDC9CA4, 0xDE09A8, 0xDE09B8]:
    print('%#010x %r' % (va, cstr(va)))
# Find dword refs to 0x84ABB08 and 0x84ABB14
for g in [0x84ABB08, 0x84ABB14, 0x84ABA60]:
    pat = struct.pack('<I', g); h=[]; i=0
    while True:
        i = d.find(pat, i)
        if i < 0: break
        v = B+i
        if 0x401000 <= v < 0xE5C8000: h.append(v)
        i += 1
    print('%#010x refs=%d %s' % (g, len(h), [hex(x) for x in h[:14]]))