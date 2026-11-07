import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
# dump strings referenced as push imm in 0xB9A9E0..0xB9B200
def cstr(va):
    o=va-B; e=d.find(b'\x00',o)
    if e<0: return None
    b=d[o:e]
    if not b: return ''
    try: return b.decode('latin1')
    except: return None
import re
va = 0xB9A9E0
o = va-B
n = 0x900
for i in range(o, o+n-5):
    if d[i]==0x68:
        t=struct.unpack_from('<I',d,i+1)[0]
        if 0xD50000 <= t < 0xDF0000:
            s=cstr(t)
            if s and len(s)>2:
                print('%#010x push %#010x %r' % (B+i, t, s[:100]))
