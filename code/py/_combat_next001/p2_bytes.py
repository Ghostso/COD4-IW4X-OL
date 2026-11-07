# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def func_start(va):
    for back in range(1, 0x900):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC:
            return x + 1
    return None

print("=== byte-width (+0x278) accesses: 0x62B653 W, 0x62F474 W, 0x62FD80 R, 0x6373D8 R, 0x63268D R ===")
for va in (0x62B653, 0x62F474, 0x62FD80, 0x6373D8, 0x63268D):
    fs = func_start(va)
    print()
    print("--- %08X (function ~%s) ---" % (va, ("%08X" % fs) if fs else "?"))
    for l in pe.dis(max(fs, va - 0x20) if fs else va - 0x20, 16):
        mark = " <<<" if l.startswith("%08X" % va) else ""
        print("   " + l + mark)
