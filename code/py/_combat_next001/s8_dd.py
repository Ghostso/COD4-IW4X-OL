# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== data-ref at fileoff 0x22DDEA (va 0x62DDEA) : find the enclosing function ===")
for back in range(0, 0x900):
    x = 0x62DDEA - back
    b = pe.read(x, 2)
    if b and b[0] == 0xCC and b[1] == 0xCC:
        print("   function start ~%08X" % (x + 1)); fs = x + 1; break
else:
    fs = 0x62DDEA - 0x400
print()
print("=== disassembly 0x%08X .. +0xB0 ===" % fs)
for l in pe.dis(fs, 80):
    print(l)
