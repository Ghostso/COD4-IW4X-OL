# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
for site in (0xC840AF, 0x658A7E):
    print("=" * 74)
    print("=== site %08X context ===" % site)
    for l in pe.dis(site - 0x70, 55):
        print(l)
    print()
