# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
for fn, nm in ((0x806F20, "slot vtable +0x00"), (0x8072A0, "slot vtable +0x04"),
               (0x806C90, "slot vtable +0x0C"), (0x8074D0, "slot vtable +0x38")):
    print("=== %s = 0x%08X ===" % (nm, fn))
    for l in pe.dis(fn, 22):
        print(l)
    print()
