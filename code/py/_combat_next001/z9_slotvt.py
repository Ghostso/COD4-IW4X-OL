# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== 槽对象的 vtable 0xDC79F0 (slots +0x00..+0x60) ===")
for i in range(0, 26):
    va = 0xDC79F0 + i*4
    v = struct.unpack("<I", pe.read(va, 4))[0]
    mark = ""
    if v in (0x637590, 0x637720, 0x6376F0, 0x637930, 0x6293B0, 0x62F6F0):
        mark = "  <<< key function"
    print("   +0x%03X  %08X%s" % (i*4, v, mark))

print()
print("=== 0xDC79FC / 0xDC7A08 的相邻表 ===")
for base in (0xDC79FC, 0xDC7A08):
    print("  base 0x%08X:" % base)
    for i in range(0, 8):
        v = struct.unpack("<I", pe.read(base + i*4, 4))[0]
        print("     +0x%02X %08X" % (i*4, v))

print()
print("=== 0x6379B0 的循环上下文（0x637950..0x6379D5） ===")
for l in pe.dis(0x637950, 45):
    print(l)
