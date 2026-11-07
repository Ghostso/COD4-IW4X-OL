#!/usr/bin/env python3
"""s138_jumptable: dump 0x636F3C 跳转表 (47 项) 与 0x82E1458 函数表."""
import struct, sys, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000


def u32(va):
    o = va - VA
    if 0 <= o <= N - 4: return struct.unpack_from("<I", d, o)[0]
    return None


def cstr(va, ml=120):
    o = va - VA
    if not (0 <= o < N - 1): return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2: return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


print("=== 跳转表 @0x636F3C (dwRoomMessage type 0..0x2e) ===")
T = 0x636F3C
for k in range(0x2f):
    v = u32(T + 4 * k)
    print("  type 0x%02X (%2d) -> 0x%08X" % (k, k, v or 0))

print("\n=== 函数表 @0x82E1458 (按 type 索引查) ===")
G = 0x82E1458
for k in range(0x2f):
    v = u32(G + 4 * k)
    if v is None: break
    if v == 0:
        print("  [%2d] 0x%08X (null)" % (k, v))
        continue
    print("  [%2d] 0x%08X" % (k, v))

print("\n=== 0x82E1408 / 0x82E1458 邻域 dword (看结构) ===")
base = 0x82E13E0
for off in range(0, 0x100, 4):
    v = u32(base + off)
    print("  0x%08X: 0x%08X" % (base + off, v))
