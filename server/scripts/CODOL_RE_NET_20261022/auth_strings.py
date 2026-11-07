import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va):
    o=va-B
    if o<0 or o>=len(d): return None
    e=d.find(b'\x00',o)
    b=d[o:e]
    if not b: return ''
    return b.decode('latin1')
def u32(va):
    o=va-B
    if o<0 or o+4>len(d): return None
    return struct.unpack('<I', d[o:o+4])[0]
# dump 0x39f13138 region refs
print('object 0x39f13138 is outside image dump? image is 0x400000..0xEA59000 ->', hex(0x400000+len(d)))
print('0x39f13138 in range:', B <= 0x39f13138 < B+len(d))
# print more auth strings 0xB9A9E0..0xB9B400
o=0xB9A9E0-B
for i in range(o, o+0x1400-5):
    if d[i]==0x68:
        t=struct.unpack_from('<I',d,i+1)[0]
        if 0xD50000 <= t < 0xDF0000:
            s=cstr(t)
            if s and len(s)>2:
                print('%#010x push %#010x %r' % (B+i, t, s[:140]))
