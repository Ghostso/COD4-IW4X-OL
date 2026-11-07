# -*- coding: utf-8 -*-
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== full vtable 0xDC72B0 .. 0xDC7470 (slots 0..0x6F) ===")
for i in range(0, 0x70):
    v = struct.unpack("<I", pe.read(0xDC72B0 + i*4, 4))[0]
    extra = ""
    if 0x62C000 <= v <= 0x63A000: extra = "  (matchmaking module)"
    print("   [%2d] +0x%03X  %08X%s" % (i, i*4, v, extra))
