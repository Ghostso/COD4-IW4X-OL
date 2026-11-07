#!/usr/bin/env python3
"""枚举 E 镜像里所有 'codo.constants' 类名, 找是否有 DW/ServiceType 之类的线上服务号常量表。"""
import re
PATH = r"E:\codol_re\client_image_20261027.bin"
data = open(PATH, "rb").read()

# AS3 字符串常量: 长度前缀(1字节) + ascii
# 直接找 "codo.constants" 出现处, 打印其后 200 字节的串
needle = b"codo.constants"
seen = set()
i = 0
cnt = 0
while True:
    p = data.find(needle, i)
    if p < 0: break
    i = p + 1
    # 取后续 300 字节, 提取可打印串
    seg = data[p:p+400]
    # 提取 ascii 串 (>=3)
    strs = re.findall(rb"[A-Za-z_][A-Za-z0-9_./:]{2,60}", seg)
    key = tuple(strs[:6])
    if key in seen: continue
    seen.add(key)
    print("@0x%X: %s" % (p, " | ".join(s.decode() for s in strs[:12])))
    cnt += 1
    if cnt > 80: break
print("\n总不同:", cnt)
