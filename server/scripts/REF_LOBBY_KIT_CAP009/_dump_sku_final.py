# -*- coding: utf-8 -*-
"""整表导出 SKU 目录 —— 判据已按手工核对修正。

★ 之前两次失败的原因:
   v1/v2 把 "sku 字段" 当成 +0x3C, 实际是 **+0x1C**;
   且 -1 判据应在 +0x0C/+0x10 (不是 +0x18/+0x1C)。

正确布局(步长 0x60, 已用 37 条连续记录逐条核对):
    +0x00 u32 price
    +0x04 u32 duration      时长(天; 0=永久)
    +0x08 u32 productId
    +0x0C u32 0xFFFFFFFF
    +0x10 u32 0xFFFFFFFF
    +0x1C u32 sku
输出: mkt_assets/sku_catalog_final.csv
"""
import csv
import os
import struct
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
OUT = os.path.join(ROOT, "mkt_assets", "sku_catalog_final.csv")
STRIDE = 0x60
NONE = 0xFFFFFFFF


def rec_at(b, off):
    if off < 0 or off + STRIDE > len(b):
        return None
    if struct.unpack_from("<I", b, off + 0x0C)[0] != NONE:
        return None
    if struct.unpack_from("<I", b, off + 0x10)[0] != NONE:
        return None
    price = struct.unpack_from("<I", b, off)[0]
    dur = struct.unpack_from("<I", b, off + 4)[0]
    pid = struct.unpack_from("<I", b, off + 8)[0]
    sku = struct.unpack_from("<I", b, off + 0x1C)[0]
    if not (1 <= sku <= 500000):
        return None
    if not (price <= 10000000 and dur <= 3650 and pid <= 1000000):
        return None
    return (sku, price, dur, pid)


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
        # ★ 找连续段: 先按 4 字节找"段起点"(自身有效、前一条无效),
        #   再按 0x60 步长向后收集。之前的 bug 是按 4 字节收集, 永远连不成段。
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
                if len(cur) >= 3:
                    rows.extend(cur)
                    segs += 1
                off = o2
            else:
                off += 4
    print("连续段 %d 个, 原始记录 %d 条" % (segs, len(rows)))

    acc = defaultdict(Counter)
    for sku, price, dur, pid in rows:
        acc[sku][(price, dur, pid)] += 1
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
    print("去重 sku: %d -> %s" % (len(final), OUT))
    print("productId 数:", len(set(r["productId"] for r in final)))
    print("时长分布:", Counter(r["duration"] for r in final).most_common(8))
    print("\n样例:")
    for r in final[:30]:
        print("   sku=%-7d price=%-8d dur=%-5d productId=%-8d (v=%d)"
              % (r["sku"], r["price"], r["duration"], r["productId"], r["votes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
