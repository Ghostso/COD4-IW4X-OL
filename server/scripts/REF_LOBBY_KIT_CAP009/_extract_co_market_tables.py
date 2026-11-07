# -*- coding: utf-8 -*-
"""解出客户端商城的 5 张真表。

mp/marketplace.json 给出清单:
    coMarketplaceItems.csv         <- 物品定义(itemID -> 名称/图标/类型)
    coMarketplaceProducts.csv      <- 商品定义(productID -> SKU)
    coMarketplaceProductItems.csv  <- productID -> itemID  ★
    coMarketplaceSKUs.csv          <- SKU 表
    coMarketplaceDiscounts.csv
每张都带一个 MD5 校验值。
"""
import hashlib
import json
import os
import re
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
OUT = os.path.join(ROOT, "mkt_assets", "co_market")
NAMES = [b"coMarketplaceItems.csv", b"coMarketplaceProducts.csv",
         b"coMarketplaceProductItems.csv", b"coMarketplaceSKUs.csv",
         b"coMarketplaceDiscounts.csv", b"unlockFlags.csv"]


def find_zlib_after(buf, pos):
    for sig in (b"\x78\xda", b"\x78\x9c", b"\x78\x01"):
        j = buf.find(sig, pos)
        if j >= 0 and j - pos < 0x400:
            try:
                d = zlib.decompressobj(15)
                out = d.decompress(buf[j:j + 8 * 1024 * 1024])
                out += d.flush()
                if out:
                    return j, out
            except Exception:
                pass
    return None, None


def main():
    os.makedirs(OUT, exist_ok=True)
    found = {}
    files = sorted(os.listdir(MEM))
    for name in NAMES:
        key = name.decode()
        for fn in files:
            p = os.path.join(MEM, fn)
            if not os.path.isfile(p):
                continue
            try:
                b = open(p, "rb").read()
            except Exception:
                continue
            i = b.find(name)
            if i < 0:
                continue
            j, data = find_zlib_after(b, i + len(name))
            if data is None:
                continue
            print("%-34s @%s:0x%X zlib@0x%X -> %d 字节"
                  % (key, fn, i, j, len(data)))
            if key not in found or len(data) > len(found[key]):
                found[key] = data
            break
    print()
    for key, data in found.items():
        out = os.path.join(OUT, key)
        with open(out, "wb") as f:
            f.write(data)
        print("%-34s -> %s (%d 字节, md5=%s)"
              % (key, out, len(data), hashlib.md5(data).hexdigest().upper()))
        # 打一行预览
        head = data[:300].decode("utf-8", "replace")
        print("   %s" % head.replace("\n", " | ")[:280])
    return 0


if __name__ == "__main__":
    sys.exit(main())
