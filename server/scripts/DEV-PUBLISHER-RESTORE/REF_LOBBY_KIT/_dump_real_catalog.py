# -*- coding: utf-8 -*-
"""按**已用 5 个真实锚点验证过**的布局, 导出客户端的商品目录。

布局(步长 0x30 = 48 字节; 用 16350/19428/31184/37251/39592 五条交叉验证):
    +0x00 u32 sku
    +0x04 u32 0
    +0x08 u32 0
    +0x0C u32 refId      (680/980/680 -> 与另一张表的 SKU 对应)
    +0x10 u32 qty        (0/0/7)
    +0x14 u32 price      (8270/16339/22384)
    +0x18 u32 0xFFFFFFFF
    +0x1C u32 0xFFFFFFFF

判据: +0x18 与 +0x1C 都是 -1, sku 合理, price 合理。
输出: mkt_assets/real_catalog.csv
"""
import csv
import os
import struct
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
OUT = os.path.join(ROOT, "mkt_assets", "real_catalog.csv")
STRIDE = 0x30
NONE = 0xFFFFFFFF


def rec_at(b, off):
    if off < 0 or off + STRIDE > len(b):
        return None
    if struct.unpack_from("<I", b, off + 0x18)[0] != NONE:
        return None
    if struct.unpack_from("<I", b, off + 0x1C)[0] != NONE:
        return None
    sku = struct.unpack_from("<I", b, off)[0]
    ref = struct.unpack_from("<I", b, off + 0x0C)[0]
    qty = struct.unpack_from("<I", b, off + 0x10)[0]
    price = struct.unpack_from("<I", b, off + 0x14)[0]
    if not (1 <= sku <= 500000):
        return None
    if not (price <= 10000000 and ref <= 5000000 and qty <= 100000):
        return None
    return (sku, ref, qty, price)


def main():
    rows = []
    segs = 0
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        off = 0
        while off + STRIDE <= len(b):
            if rec_at(b, off) and not rec_at(b, off - STRIDE):
                cur = []
                o2 = off
                while True:
                    r = rec_at(b, o2)
                    if r is None:
                        break
                    cur.append(r)
                    o2 += STRIDE
                if len(cur) >= 2:
                    rows.extend(cur)
                    segs += 1
                off = o2
            else:
                off += 4
    print("连续段 %d, 原始 %d 条" % (segs, len(rows)))
    acc = defaultdict(Counter)
    for sku, ref, qty, price in rows:
        acc[sku][(ref, qty, price)] += 1
    final = []
    for sku, c in sorted(acc.items()):
        (ref, qty, price), votes = c.most_common(1)[0]
        final.append({"sku": sku, "refId": ref, "qty": qty,
                      "price": price, "votes": votes})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "refId", "qty", "price", "votes"])
        w.writeheader()
        w.writerows(final)
    print("去重 sku: %d -> %s" % (len(final), OUT))
    print("价格分布 top:", Counter(r["price"] for r in final).most_common(8))
    print("\n样例:")
    for r in final[:30]:
        print("   sku=%-7d ref=%-7d qty=%-4d price=%-8d (v=%d)"
              % (r["sku"], r["refId"], r["qty"], r["price"], r["votes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
