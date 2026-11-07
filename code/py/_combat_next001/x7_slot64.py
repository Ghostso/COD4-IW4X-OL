# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
R = "eax ecx edx ebx esp ebp esi edi".split()

print("=== 0x62DD5F 在哪个 vtable 槽？（扫描主 vtable 0xDC7274 全表找它） ===")
found = False
for i in range(0, 0x80):
    va = 0xDC7274 + i*4
    v = struct.unpack("<I", pe.read(va, 4))[0]
    if v == 0x62DD5F:
        print("   slot +0x%03X = 0x62DD5F" % (i*4)); found = True
if not found:
    print("   不在 0xDC7274 起的 0x200 字节内；试 0xDC72B0 视点：")
    for i in range(0, 0x80):
        va = 0xDC72B0 + i*4
        v = struct.unpack("<I", pe.read(va, 4))[0]
        if v == 0x62DD5F:
            print("   0xDC72B0 view slot +0x%03X = 0x62DD5F" % (i*4)); found = True
if not found:
    print("   两表均未命中 —— 需扩大搜索")
    for base, nm in ((0xDC7274, "primary"),):
        for i in range(0, 0x400):
            va = base + i*4
            b = pe.read(va, 4)
            if not b: break
            if struct.unpack("<I", b)[0] == 0x62DD5F:
                print("   %s slot +0x%03X" % (nm, i*4)); found = True

print()
print("=== 'call dword ptr [reg+0x64]' 命中（验证性检查） ===")
n = 0
for o in range(len(d) - 7):
    if d[o] != 0xFF: continue
    m = d[o+1]
    if (m & 0x38) != 0x10: continue
    mod = m >> 6; rm = m & 7
    if rm == 4: continue
    if mod == 1:
        if struct.unpack_from("<b", d, o+2)[0] != 0x64: continue
    elif mod == 2:
        if struct.unpack_from("<i", d, o+2)[0] != 0x64: continue
    else:
        continue
    va = pe.off_to_va(o)
    if va and pe.is_exec(va):
        n += 1
        if n <= 20: print("   %08X call [%s+0x64]" % (va, R[rm]))
print("   total =", n)
