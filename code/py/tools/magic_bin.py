#!/usr/bin/env python3
"""在客户端二进制里搜魔数 A/B 的出现点（小端 4 字节），定位它们的产生/比较代码。"""
import struct
import sys

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
A = 0xD692ADAB
B = 0x8D51E398
A2 = 0xABAD92D6  # 若被当成有符号立即数
B2 = 0x98E3518D

data = open(PATH, "rb").read()
print("file size = %d (0x%X)" % (len(data), len(data)))

targets = {
    "A_le": struct.pack("<I", A),
    "B_le": struct.pack("<I", B),
}
for name, pat in targets.items():
    idx = 0
    hits = []
    while True:
        p = data.find(pat, idx)
        if p < 0:
            break
        hits.append(p)
        idx = p + 1
    print("\n%s pattern=%s  hits=%d" % (name, pat.hex(), len(hits)))
    for h in hits[:40]:
        # 打印上下文
        lo = max(0, h - 16)
        ctx = data[lo:h + 20]
        print("  off=0x%08X file_va=0x%08X ctx=%s" % (h, h + 0x400000, ctx.hex()))

# 也搜 8 字节形式（若两魔数相邻）
pat8 = struct.pack("<II", A, B)
print("\nAB adjacent 8B hits = %d" % data.count(pat8))
pat8b = struct.pack("<II", B, A)
print("BA adjacent 8B hits = %d" % data.count(pat8b))
