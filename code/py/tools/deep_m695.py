#!/usr/bin/env python3
"""-695030357 (21/5 findSessions 里的值) 深挖: 0xD68... 形态? 与魔数A 0xD692ADAB 关系?"""
V=-695030357
print("V = %d = 0x%08X" % (V, V & 0xffffffff))
print("bits:", bin(V & 0xffffffff))
A=0xD692ADAB
print("\n魔数A 0xD692ADAB = %d" % A)
print("V xor A = 0x%08X" % ((V & 0xffffffff) ^ A))
print("V - A = %d" % ((V & 0xffffffff) - A))
print("V & 0xFFFF = 0x%04X" % ((V&0xffff)))
print("V >> 16 = 0x%04X" % ((V>>16)&0xffff))
print("A >> 16 = 0x%04X" % ((A>>16)&0xffff))
# 高16位比较
print("\nV高16=0x%04X  A高16=0x%04X" % ((V>>16)&0xffff, (A>>16)&0xffff))
# 是不是 -695030357 = -(695030357)? 695030357 hex?
print("695030357 = 0x%08X" % 695030357)
