# -*- coding: utf-8 -*-
"""0x5C0DB1 / 0x5C0E79 在 move [ebx+0x28] 附近 —— 这是 battle 状态机里的调用！"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

for site in (0x5C0DB1, 0x5C0E79):
    print("=" * 74)
    print("=== site %08X context ===" % site)
    for l in pe.dis(site - 0x40, 42):
        print(l)
    print()
