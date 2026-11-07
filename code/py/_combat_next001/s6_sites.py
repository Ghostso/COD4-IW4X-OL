# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
for site in (0x58754D, 0x7FF7BA):
    print("=" * 74)
    print("=== call site %08X (context) ===" % site)
    for l in pe.dis(site - 0x50, 40):
        print(l)
    print()
