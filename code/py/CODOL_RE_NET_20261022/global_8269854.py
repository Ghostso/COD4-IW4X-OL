import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def u32(va): return struct.unpack('<I', d[va-B:va-B+4])[0]
def cstr(va):
    o=va-B; e=d.find(b'\x00',o); return d[o:e].decode('latin1','replace')
p = u32(0x8269854)
print('0x8269854 ->', hex(p))
if p:
    print('  [+0xc] ->', hex(u32(p+0xc)))
    print('  str:', repr(cstr(u32(p+0xc))))
# find refs to 0x8269854
pat = struct.pack('<I', 0x8269854); h=[]; i=0
while True:
    i = d.find(pat, i)
    if i < 0: break
    v = B+i
    if 0x401000 <= v < 0xE5C8000: h.append(v)
    i += 1
print('refs:', [hex(x) for x in h[:20]])
