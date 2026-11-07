# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def cstr(va, maxn=160):
    b = pe.read(va, maxn)
    if not b: return None
    z = b.find(b"\0")
    return b[:z if z >= 0 else maxn].decode("latin1", "replace")

print("=== context around 0xXC5D7CA (udp:// handler) ===")
for l in pe.dis(0xC5D760, 60):
    print(l)
print()
print("=== strings nearby in 0xC5D6xx..0xC5DAxx ===")
for va in range(0xC5D600, 0xC5DA00, 1):
    pass
start = 0xC5D600
off = pe.va_to_off(start)
cur = off
s0 = cur
end = pe.va_to_off(0xC5DA00)
while cur < end:
    if pe.data[cur] == 0:
        if cur > s0:
            s = pe.data[s0:cur]
            if 2 <= len(s) <= 60 and all(32 <= c < 127 for c in s):
                print("   %08X %s" % (pe.off_to_va(s0), s.decode("latin1")))
        s0 = cur + 1
    cur += 1
