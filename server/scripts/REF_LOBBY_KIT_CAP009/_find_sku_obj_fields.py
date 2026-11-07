# -*- coding: utf-8 -*-
"""找客户端 SKU/商品对象的字段定义 —— 看 Category 叫什么、在哪。

已知接口: AS_GetItemInfoBySku / AS_GetItemIDsFromProduct
目标: 找到商品对象的字段表(类似 CallSignObj 那种 ActionScript 元数据)。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
KEYS = [b"AS_GetItemInfoBySku", b"AS_GetItemIDsFromProduct",
        b"AS_GetProductIDFromSKU", b"category", b"Category",
        b"itemCategory", b"skuCategory", b"itemType", b"productType"]


def main():
    b = open(P, "rb").read()
    for key in KEYS:
        print("=" * 76)
        i = b.find(key)
        if i < 0:
            print("%s: 没找到" % key.decode())
            continue
        print("%s @0x%X" % (key.decode(), i))
        lo = max(0, i - 0x180)
        hi = min(len(b), i + 0x260)
        strs = re.findall(rb"[ -~]{3,90}", b[lo:hi])
        for s in strs[:40]:
            print("    %s" % s.decode("latin1"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
