#!/usr/bin/env python3
"""s138_servtable: 解析 [fn][svc][a][b] 16 字节记录表 @0xE53000~, 列出 svc 与 a/b."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000, 0x401000 + 0x8a689a

def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

# find start: scan backwards from 0xE53024 while pattern holds
start = 0xE53024
while start - 16 >= 0:
    fn = u32(start - 16)
    if fn and TL <= fn < TH:
        start -= 16
    else:
        break
print("table starts ~0x%X" % start)

end = start
while True:
    fn = u32(end)
    svc = u32(end + 4)
    a = u32(end + 8)
    b = u32(end + 12)
    if fn is None or not (TL <= fn < TH):
        break
    if svc is None or svc > 200: break
    end += 16

print("table ends ~0x%X  entries=%d" % (end, (end - start)//16))
for va in range(start, end, 16):
    fn = u32(va); svc = u32(va+4); a = u32(va+8); b = u32(va+12)
    print("  0x%08X fn=0x%08X svc=%-3d a=%-3d b=%-3d" % (va, fn, svc, a, b))
