#!/usr/bin/env python3
"""Base.dll: 转储 ServiceID 附近上下文, 找服务名串表。"""
PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
data = open(PATH, "rb").read()

def show(o, pre=64, post=200):
    lo = max(0, o-pre); hi = min(len(data), o+post)
    seg = data[lo:hi]
    s = "".join(chr(b) if 32 <= b < 127 else "." for b in seg)
    print("--- @0x%X ---" % o)
    print(s)

for o in [0x95675F, 0x956837, 0xA00BA2, 0xA00CF1, 0xA00EBA]:
    show(o)
    print()
