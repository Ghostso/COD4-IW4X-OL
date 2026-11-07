import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va):
    o=va-B; e=d.find(b'\x00',o); return d[o:e].decode('latin1','replace')
targets = {}
va = 0xDE0980
while va < 0xDE0B00:
    s = cstr(va)
    if s:
        targets[va] = s
        va += len(s)+1
    else:
        va += 1
for va,s in targets.items():
    pat = struct.pack('<I', va); h=[]; i=0
    while True:
        i = d.find(pat, i)
        if i < 0: break
        v = B+i
        if 0x401000 <= v < 0xE5C8000: h.append(v)
        i += 1
    print('%#010x %-45r refs=%s' % (va, s[:45], [hex(x) for x in h[:8]]))