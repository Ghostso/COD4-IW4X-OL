# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== 主 vtable 0xDC7274 : 相关槽位总表 ===")
want = {0x632680:"accepted handler", 0x63794F:"MUST be 0x637950",
        0x637950:"BATCH SLOT COPY", 0x6379E0:"wrapper -> batch copy",
        0x637720:"slot writer (2)", 0x637590:"slot writer (1)",
        0x6376F0:"slot filler via timer 0x27", 0x637930:"slot filler 0x27",
        0x62DE90:"registers task 0x32", 0x62DE80:"fires task 0x26",
        0x6292B0:"takes (callback, timerId)", 0x6293B0:"BRIDGE",
        0x62F840:"booking entry"}

for i in range(0, 0x60):
    va = 0xDC7274 + i*4
    v = struct.unpack("<I", pe.read(va, 4))[0]
    if v in want:
        print("   vtable +0x%03X  %08X   %s" % (i*4, v, want[v]))

print()
print("=== 确认 0xEEQ: 0x637950 是否出现在 vtable 中 ===")
for base in (0xDC7274,):
    for i in range(0, 0x200):
        v = struct.unpack("<I", pe.read(base + i*4, 4))[0]
        if v == 0x637950:
            print("   0xDC7274 +0x%03X = 0x637950" % (i*4))
        if v == 0x6379E0:
            print("   0xDC7274 +0x%03X = 0x6379E0" % (i*4))

print()
print("=== 0x6292B0 的四个调用点：(callback, id) 配对 ===")
for v in pe.calls_to(0x6292B0):
    seg = pe.read(v - 0x10, 0x14)
    print("   call@%08X  prev bytes: %s" % (v, seg.hex()))
