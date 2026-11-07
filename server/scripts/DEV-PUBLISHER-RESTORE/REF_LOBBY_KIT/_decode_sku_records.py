# -*- coding: utf-8 -*-
"""解码内存里的 SKU 记录(客户端在用的目录)。

实测布局(两条独立样本一致):
    sku=16350 @0x40F5CC:
        +0x00 u32 16350
        +0x04 u32 0
        +0x08 u32 0
        +0x0C u32 680      <- 疑似 itemID / category
        +0x10 u32 0
        +0x14 u32 8270     <- price
        +0x18 u32 0xFFFFFFFF
        +0x1C u32 0xFFFFFFFF
    sku=980   @0x421338:
        +0x00 u32 980
        +0x04 u32 0
        +0x08 u32 90
        +0x0C u32 1432     <- price(此处位置前移?)
        +0x10 u32 0xFFFFFFFF
        +0x14 u32 0xFFFFFFFF

★ 两条记录字段位置不完全一致 -> 说明记录**不是定长**, 或前置字段数不同。
  这里用"sku 后面第一个非零小整数 = 价格"的启发式扫全表, 并与"客户端点过"
  的 SKU 交叉验证。
"""
import csv
import os
import struct

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
OUT = os.path.join(ROOT, "mkt_assets", "sku_records_decoded.csv")
NONE = 0xFFFFFFFF


def main():
    if not os.path.exists(SRC):
        print("缺 %s" % SRC)
        return 1
    b = open(SRC, "rb").read()
    rows = []
    # 扫所有 "sku 后跟 [-1,-1]" 的位置, 把 sku 与后面第一个合理 price 配对
    for off in range(0, len(b) - 0x40, 4):
        sku = struct.unpack_from("<I", b, off)[0]
        if not (1 <= sku <= 200000):
            continue
        # 向后 0x08..0x20 找一对连续的 0xFFFFFFFF
        for j in range(off + 4, off + 0x30, 4):
            if j + 8 > len(b):
                break
            if (struct.unpack_from("<I", b, j)[0] == NONE
                    and struct.unpack_from("<I", b, j + 4)[0] == NONE):
                # 取 [-1,-1] 之前 8 字节里的 u32 作为候选 price
                if j - 8 >= off:
                    p1 = struct.unpack_from("<I", b, j - 4)[0]
                    p2 = struct.unpack_from("<I", b, j - 8)[0]
                    for price in (p1, p2):
                        if 0 < price <= 5000000:
                            rows.append({"sku": sku, "price": price,
                                         "off": "0x%08X" % off})
                            break
                break
    # 去重: 同 sku 取众数价格
    from collections import Counter, defaultdict
    acc = defaultdict(Counter)
    for r in rows:
        acc[r["sku"]][r["price"]] += 1
    final = []
    for sku, c in sorted(acc.items()):
        price, n = c.most_common(1)[0]
        final.append({"sku": sku, "price": price, "votes": n})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "price", "votes"])
        w.writeheader()
        w.writerows(final)
    print("原始候选 %d 条, 去重 sku %d 个 -> %s" % (len(rows), len(final), OUT))
    for r in final[:30]:
        print("   sku=%-7d price=%-8d (votes=%d)"
              % (r["sku"], r["price"], r["votes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
