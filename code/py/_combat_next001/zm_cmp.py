# -*- coding: utf-8 -*-
"""对比 0x7FA640 的两个调用点，看哪个实参随"条目"而变 —— 用于判定数组来源。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== 0x7FA640 读取的入参偏移（来自函数体）===")
for l in pe.dis(0x7FA640, 90):
    if "[ebp +" in l:
        print("   " + l)

print()
print("=== 调用点 A: 0x7FA8A8 之前（0x7FA860..0x7FA8A8）===")
for l in pe.dis(0x7FA860, 30):
    print("   " + l)

print()
print("=== 调用点 B: 0x7FA95A 之前（0x7FA918..0x7FA95A）===")
for l in pe.dis(0x7FA918, 30):
    print("   " + l)
