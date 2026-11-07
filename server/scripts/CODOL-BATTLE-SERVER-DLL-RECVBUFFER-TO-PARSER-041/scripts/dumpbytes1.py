# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
data = raw(0x230F60, 0x120)
print("bytes 0x230F60..0x231080:")
for i in range(0, len(data), 16):
    chunk = data[i:i+16]
    rva = 0x230F60 + i
    print("0x%06X  %s" % (rva, " ".join("%02x"%c for c in chunk)))
