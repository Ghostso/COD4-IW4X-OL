# -*- coding: utf-8 -*-
"""精确验证：0x7FA9B0 处 esi/edi 的取值来源（判断"arg6 来自条目内部偏移"的等级）。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== 0x7FA860 .. 0x7FA9B5 : esi/edi/ebp-相对 的全部写入（逐指令）===")
for l in pe.dis(0x7FA860, 100):
    print(l)
