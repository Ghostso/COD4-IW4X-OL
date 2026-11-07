# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data

def cstr(va, maxn=120):
    b = pe.read(va, maxn)
    if not b: return None
    z = b.find(b"\0")
    return b[:z if z >= 0 else maxn].decode("latin1", "replace")

print("=== key strings used by the handshake map builder ===")
for va in (0xDB4530, 0xDBFD18, 0xDBFD20, 0xDBFD28, 0xDB4B60, 0xDBC0F4,
           0xDBFD30, 0xDBFD34, 0xDBFD3C, 0xDBFD48, 0xDBFD54, 0xDBFD5C,
           0xDA0CDC, 0xDAE091, 0xDBFD04, 0xDBFD08, 0xDBFD10):
    print("  %08X  %r" % (va, cstr(va)))

# 找包含 0x5C08E0 的函数起点：往回扫描 int3/对齐填充后的第一条指令
print()
print("=== function start search for 0x5C08E0 ===")
start = 0x5C08E0
for back in range(1, 0x600):
    va = start - back
    b = pe.read(va - 1, 2)
    if b and b[0] == 0xCC and b[1] == 0xCC:
        print("  candidate after int3 pad: %08X" % va)
        break
# 也打印该地址之前 64 字节
print()
print("=== 0x5C05E0 .. 0x5C06E0 ===")
for l in pe.dis(0x5C05E0, 50):
    print(l)
