# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== function containing 0x470467 (state=3 write) ===")
for l in pe.dis(0x470410, 80):
    print(l)
print()
print("=== callers of the enclosing function (search back for prologue) ===")
# 向上找 int3 填充后的函数起点
start = 0x470467
for back in range(1, 0x800):
    va = start - back
    b = pe.read(va, 2)
    if b and b[0] == 0xCC and b[1] == 0xCC:
        print("  likely func entry after padding: %08X" % (va + 1))
        break
