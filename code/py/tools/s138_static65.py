#!/usr/bin/env python3
"""s138_static65: 按 24 字节记录解析含 (6,5,20) 的静态表."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000

def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

# find 6,5,20 at 0x82C8B18. Base aligned to 24
anchor = 0x82C8B18
print("=== 记录步长 24B, 从 anchor 回溯到表首 ===")
# scan backwards for table start: first record where svc.. plausible
start = anchor
while start - 24 >= 0:
    svc = u32(start - 24)
    if svc is None or svc > 200: break
    start -= 24
# extend
first = start
while first - 24 >= 0 and (u32(first-24) is not None and u32(first-24) <= 200 and (u32(first-20) if u32(first-20) is not None else 999) <= 200):
    first -= 24

print("first guess 0x%X" % first)
for va in range(anchor - 24*20, anchor + 24*30, 24):
    a,b,c,e,f,g = (u32(va+4*i) for i in range(6))
    mark = " <== 6/5" if (a==6 and b==5) else ""
    print("  0x%08X: %-4s %-4s %-5s %-4s %-4s %-5s%s" % (va, a,b,c,e,f,g, mark))
