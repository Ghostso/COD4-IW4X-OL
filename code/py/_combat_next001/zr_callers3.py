# -*- coding: utf-8 -*-
"""分析 0x7FA800 三个业务调用点的完整参数装配与源结构。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def fs(va):
    for back in range(1, 0x1500):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC: return x + 1
    return None

for site in (0x4A8E01, 0x4AA8D8, 0x4B56E1):
    f = fs(site)
    print("=" * 76)
    print("=== site %08X  (function ~%s) ===" % (site, hex(f) if f else "?"))
    # 找函数序言开始处打印
    start = max(f, site - 0x100) if f else site - 0x100
    for l in pe.dis(start, 70):
        print(l)
    print()
