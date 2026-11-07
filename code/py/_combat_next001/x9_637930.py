# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
for site, label in ((0x632721, "accepted handler 0x632680 region"),
                    (0x62F94A, "0x62F840 region"),
                    (0x62FBD0, "0x62FB9F region")):
    print("=" * 74)
    print("=== ref to 0x637930 at %08X  (%s) ===" % (site, label))
    for l in pe.dis(site - 0x40, 40):
        print(l)
    print()
