# -*- coding: utf-8 -*-
"""整表导出客户端的 SKU 目录(内存里那张 96 字节步长的表)。

实测布局(步长 0x60, 来自 r_259D0000_06400000.bin 的连续区段):
    +0x00 u32 price         价格
    +0x04 u32 duration      时长(天; 0=永久)
    +0x08 u32 productId     商品ID
    +0x18 u32 0xFFFFFFFF
    +0x1C u32 0xFFFFFFFF
    +0x20 u32 指针
    +0x24 u32 0
    +0x28 u32 ?
    +0x3C u32 sku           本条 SKU 编号

判据: +0x18/+0x1C 都是 0xFFFFFFFF, 且 +0x3C 是合理 sku。
输出: mkt_assets/full_sku_table.csv
"""
import csv
import os
import struct
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
OUT = os.path.join(ROOT, "mkt_assets", "full_sku_table.csv")
STRIDE = 0x60
NONE = 0xFFFFFFFF


def scan(b, fn, out):
    n = 0
    limit = len(b) - STRIDE
    off = 0
    while off <= limit:
        a = struct.unpack_from("<I", b, off + 0x18)[0]
        if a == NONE:
            c = struct.unpack_from("<I", b, off + 0x1C)[0]
            if c == NONE:
                sku = struct.unpack_from("<I", b, off + 0x3C)[0]
                if 1 <= sku <= 500000:
                    price = struct.unpack_from("<I", b, off)[0]
                    dur = struct.unpack_from("<I", b, off + 4)[0]
                    pid = struct.unpack_from("<I", b, off + 8)[0]
                    if price <= 50000000 and dur <= 3650 and pid <= 5000000:
                        out.append({"sku": sku, "price": price, "duration": dur,
                                    "productId": pid, "src": fn,
                                    "off": "0x%08X" % off})
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
        scan(b, fn, rows)
    print("扫描 %d 区, 原始 %d 条" % (files, len(rows)))

    # 同 sku 取众数(价格/时长/商品)
    from collections import defaultdict
    acc = defaultdict(Counter)
    for r in rows:
        acc[r["sku"]][(r["price"], r["duration"], r["productId"])] += 1
    final = []
    for sku, c in sorted(acc.items()):
        (price, dur, pid), votes = c.most_common(1)[0]
        final.append({"sku": sku, "price": price, "duration": dur,
                      "productId": pid, "votes": votes})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "price", "duration", "productId", "votes"])
        w.writeheader()
        w.writerows(final)
    print("去重后 SKU 数: %d -> %s" % (len(final), OUT))
    print("\n时长分布:", Counter(r["duration"] for r in final).most_common(8))
    print("\n样例:")
    for r in final[:25]:
        print("   sku=%-7d price=%-8d dur=%-4d productId=%-8d (v=%d)"
              % (r["sku"], r["price"], r["duration"], r["productId"], r["votes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
