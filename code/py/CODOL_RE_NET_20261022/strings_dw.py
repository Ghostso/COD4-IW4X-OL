import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
def cstr(va):
    o=va-B; e=d.find(b'\x00',o); return d[o:e].decode('latin1','replace')
# print strings in 0xdb0000..0xde0000 that look like lobby/net
import re
pat = re.compile(rb'[\x20-\x7e]{6,}')
seg = d[0xDB0000-B:0xDE0000-B]
for m in pat.finditer(seg):
    s = m.group().decode('latin1')
    if any(k in s.lower() for k in ['dwlobby','dw_','lobby','bdaddr','bd_address','session','matchmaking','gamestate','connect','socket','netchan','packet','reliable','auth','login','ticket','blaze']):
        print('%#010x %s' % (0xDB0000+m.start(), s[:110]))