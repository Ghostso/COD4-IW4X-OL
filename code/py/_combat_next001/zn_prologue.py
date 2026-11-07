# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x7FA800 序言 (0x7FA800..0x7FA860) : 全部 [ebp+NN] 的处理 ===")
for l in pe.dis(0x7FA800, 70):
    print(l)
