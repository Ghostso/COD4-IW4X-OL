# -*- coding: utf-8 -*-
"""定位客户端"商城表"在内存里的结构与加载点。

已知:
  - 客户端用 AS_GetProductIDFromSKU / AS_GetItemIDsFromProduct 查 SKU -> item
  - exe 目录(marketplace-catalog.json)覆盖不全, 缺那批可点的 SKU
  - 客户端实际能点到它们 -> 客户端内部有更全的表

思路: 搜客户端加载商城表时的资源名/表名, 以及表的字段名。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
KEYS = [b"marketplace", b"marketplace_", b"mp/market", b"item_sku",
        b"skuTable", b"productTable", b"mktTable", b"storeTable",
        b"getSkusPaginated", b"AS_GetProductIDFromSKU"]


def main():
    for key in KEYS:
        print("=" * 76)
        print("KEY %s" % key.decode())
        n = 0
        for fn in sorted(os.listdir(MEMDIR)):
            p = os.path.join(MEMDIR, fn)
            if not os.path.isfile(p):
                continue
            try:
                b = open(p, "rb").read()
            except Exception:
                continue
            i = b.find(key)
            if i < 0:
                continue
            n += 1
            if n > 3:
                break
            print("  %s @0x%X" % (fn, i))
            lo = max(0, i - 150)
            hi = min(len(b), i + 250)
            strs = re.findall(rb"[ -~]{5,90}", b[lo:hi])
            for s in strs[:28]:
                print("      %s" % s.decode("latin1"))
        if n == 0:
            print("  (无)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
