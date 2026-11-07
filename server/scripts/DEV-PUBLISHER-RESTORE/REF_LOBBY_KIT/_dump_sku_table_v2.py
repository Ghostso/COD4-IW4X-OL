# -*- coding: utf-8 -*-
"""按**已确认的布局**整表导出 SKU 目录(步长 0x60)。

布局(用连续 12 条记录交叉验证过, 字段自洽):
    +0x00 u32 price
    +0x04 u32 duration      时长(天; 0=永久)
    +0x08 u32 productId
    +0x0C u32 0xFFFFFFFF
    +0x10 u32 0xFFFFFFFF
    +0x14 u32 指针
    +0x18 u32 0
    +0x1C u32 sku           <- 本条 SKU 编号

判据(比 v1 严得多, 专治噪声):
  1) +0x0C 与 +0x10 都是 0xFFFFFFFF
  2) +0x1C 是合理 sku (1..500000)
  3) price <= 10,000,000 且 duration <= 3650 且 productId <= 1,000,000
  4) 同一 sku 的 (price,duration,productId) 必须**多次一致**(votes>=2)
"""
import csv
import os
import struct
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
OUT = os.path.join(ROOT, "mkt_assets", "full_sku_table_v2.csv")
STRIDE = 0x60
NONE = 0xFFFFFFFF


def scan(b, fn, out):
    n = 0
    off = 0
    limit = len(b) - STRIDE
    while off <= limit:
        if (struct.unpack_from("<I", b, off + 0x0C)[0] == NONE
                and struct.unpack_from("<I", b, off + 0x10)[0] == NONE):
            sku = struct.unpack_from("<I", b, off + 0x1C)[0]
            price = struct.unpack_from("<I", b, off)[0]
            dur = struct.unpack_from("<I", b, off + 4)[0]
            pid = struct.unpack_from("<I", b, off + 8)[0]
            if (1 <= sku <= 500000 and price <= 10000000
                    and dur <= 3650 and pid <= 1000000):
                out.append((sku, price, dur, pid))
                n += 1
        off += 4
    return n


def main():
    rows = []
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        scan(b, fn, rows)
    print("原始 %d 条" % len(rows))
    acc = defaultdict(Counter)
    for sku, price, dur, pid in rows:
        acc[sku][(price, dur, pid)] += 1
    final = []
    for sku, c in sorted(acc.items()):
        (price, dur, pid), votes = c.most_common(1)[0]
        if votes >= 2:                      # ★ 只保留多次一致的
            final.append({"sku": sku, "price": price, "duration": dur,
                          "productId": pid, "votes": votes})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "price", "duration", "productId", "votes"])
        w.writeheader()
        w.writerows(final)
    print("多次一致(>=2)的 sku: %d -> %s" % (len(final), OUT))
    print("时长分布:", Counter(r["duration"] for r in final).most_common(10))
    print("商品数:", len(set(r["productId"] for r in final)))
    print("\n样例:")
    for r in final[:30]:
        print("   sku=%-7d price=%-8d dur=%-5d productId=%-8d (v=%d)"
              % (r["sku"], r["price"], r["duration"], r["productId"], r["votes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
