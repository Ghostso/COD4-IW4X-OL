# -*- coding: utf-8 -*-
"""检查 0x7FA800 的三个业务调用点：传入的哪个参数是 0x238 记录数组。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== 0x7FA800 全部 7 个调用点 ===")
for v in pe.calls_to(0x7FA800):
    print("   %08X" % v)
print()
for site in (0x4A8E01, 0x4AA8D8, 0x4B56E1):
    print("=" * 74)
    print("=== business caller site %08X ===" % site)
    for l in pe.dis(site - 0x48, 46):
        print(l)
    print()
