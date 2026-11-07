#!/usr/bin/env python3
"""深挖 0x35BB000 区域: 疑似 DWServiceStatus 的 AS3 常量表 (含 'messaging'/'status')。
按 [len u8][ascii] 解析整块，还原所有服务名/字段名。
"""
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N = len(data)

def dump_strings(lo, hi, label):
    print("=== %s 0x%X-0x%X : 解析 [len][ascii] ===" % (label, lo, hi))
    i = lo
    out = []
    while i < hi:
        L = data[i]
        if 1 <= L <= 64 and i+1+L <= N:
            s = data[i+1:i+1+L]
            if all(32 <= b < 127 for b in s):
                out.append((i, s.decode("latin1")))
                i += 1 + L
                continue
        i += 1
    for off, s in out:
        print("  0x%08X  %r" % (off, s))
    print()

# 大范围扫描 0x35B0000-0x35C0000, 收集长度前缀串
dump_strings(0x35B0000, 0x35C0000, "AS3 const table wide")
