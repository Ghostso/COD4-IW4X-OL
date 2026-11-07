# -*- coding: utf-8 -*-
"""从内存转储里把客户端**真正在用的 SKU 目录**整表捞出来。

记录布局(步长 0x60 = 96 字节, 实测):
    +0x00 u32 sku
    +0x0C u32 (category/duration 类)
    +0x10 u32
    +0x14 u32 price          <- 0xFFFFFFFF 表示未定价
    +0x18 u32 0xFFFFFFFF
    +0x1C u32 0xFFFFFFFF

★ 关键: 价格 != 0xFFFFFFFF 的才是**真目录项**(可购买)。
输出: mkt_assets/sku_catalog_from_mem.csv
"""
import csv
import os
import struct
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
OUT = os.path.join(ROOT, "mkt_assets", "sku_catalog_from_mem.csv")
STRIDE = 0x60
PRICE_NONE = 0xFFFFFFFF


def scan_buffer(b, fn, out):
    n = 0
    limit = len(b) - STRIDE
    off = 0
    while off <= limit:
        sku = struct.unpack_from("<I", b, off)[0]
        if 100 <= sku <= 200000:
            a = struct.unpack_from("<I", b, off + 0x18)[0]
            c = struct.unpack_from("<I", b, off + 0x1C)[0]
            if a == PRICE_NONE and c == PRICE_NONE:
                f0c = struct.unpack_from("<I", b, off + 0x0C)[0]
                f10 = struct.unpack_from("<I", b, off + 0x10)[0]
                price = struct.unpack_from("<I", b, off + 0x14)[0]
                out.append({"sku": sku, "price": price, "f0C": f0c,
                            "f10": f10, "src": fn, "off": "0x%08X" % off})
                n += 1
        off += 4
    return n


def main():
    rows = []
    files = 0
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        files += 1
        scan_buffer(b, fn, rows)
    print("扫描 %d 个区, 原始命中 %d 条" % (files, len(rows)))

    # 去重: 同一 sku 取"价格有效"的那条
    best = {}
    for r in rows:
        k = r["sku"]
        cur = best.get(k)
        if cur is None:
            best[k] = r
        else:
            # 优先保留 price 有效的
            if cur["price"] == PRICE_NONE and r["price"] != PRICE_NONE:
                best[k] = r
    print("去重后 sku 数: %d" % len(best))

    priced = {k: v for k, v in best.items() if v["price"] != PRICE_NONE}
    print("其中**价格有效**(可真买)的: %d" % len(priced))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["sku", "price", "f0C", "f10", "src", "off"])
        w.writeheader()
        for k in sorted(priced):
            w.writerow(priced[k])
    print("导出 -> %s" % OUT)

    # 价格分布(看像不像真实定价)
    pc = Counter(v["price"] for v in priced.values())
    print("\n最常见价格:")
    for p, c in pc.most_common(12):
        print("   %-8d x%d" % (p, c))
    print("\nsku 区间: %d .. %d" % (min(priced), max(priced)))
    print("\n样例:")
    for k in sorted(priced)[:20]:
        v = priced[k]
        print("   sku=%-7d price=%-8d f0C=%-6d f10=%d"
              % (k, v["price"], v["f0C"], v["f10"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
