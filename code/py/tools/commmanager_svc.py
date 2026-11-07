#!/usr/bin/env python3
"""CommManager.preInit 服务注册序列: 0x352FA00 起完整服务名清单 (注册顺序)。"""
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N=len(data)
i = 0x352F9F0
hi = 0x352FC00
print("=== [len][name] 解析 0x%X-0x%X ===" % (i, hi))
out=[]
while i < hi:
    L = data[i]
    if 1 <= L <= 64 and i+1+L <= N and all(32 <= b < 127 for b in data[i+1:i+1+L]):
        out.append((i, data[i+1:i+1+L].decode("latin1")))
        i += 1+L
        continue
    i += 1
for off,s in out:
    print("  0x%08X  %r" % (off, s))
