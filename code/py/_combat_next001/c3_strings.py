# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
print("=== strings near the handshake field table (0xDB4B00..0xDBFE00) ===")
base = 0xDB4B00
end = 0xDBFE00
off = pe.va_to_off(base)
cur = off
start = cur
while cur < pe.va_to_off(end):
    if d[cur] == 0:
        if cur > start:
            s = d[start:cur]
            if 2 <= len(s) <= 40 and all(32 <= c < 127 for c in s):
                va = pe.off_to_va(start)
                if va and va in (0xD90B14,) or True:
                    pass
                print("  %08X  %s" % (pe.off_to_va(start), s.decode("latin1")))
        start = cur + 1
    cur += 1
