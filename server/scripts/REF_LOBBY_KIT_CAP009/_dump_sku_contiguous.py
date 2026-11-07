# -*- coding: utf-8 -*-
"""只导出**连续的那张 SKU 表**(不做全盘扫描, 避免噪声)。

锚点: r_259D0000_06400000.bin @0x421338 (已知自洽的 12 条记录起点)
布局(步长 0x60):
    +0x00 price / +0x04 duration / +0x08 productId
    +0x0C -1 / +0x10 -1 / +0x14 指针 / +0x18 0 / +0x1C sku

做法: 从锚点向前后**逐个**读, 结构不成立即停 —— 这样得到的是表的真实边界。
"""
import csv
import os
import struct

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
OUT = os.path.join(ROOT, "mkt_assets", "sku_table_contiguous.csv")
STRIDE = 0x60
NONE = 0xFFFFFFFF


def rec_at(b, off):
    """读一条; 结构不成立返回 None。"""
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
    return {"sku": sku, "price": price, "duration": dur, "productId": pid}


def main():
    if not os.path.exists(SRC):
        print("缺 %s" % SRC)
        return 1
    b = open(SRC, "rb").read()
    anchor = 0x421338

    # 向后读
    fwd = []
    off = anchor
    while True:
        r = rec_at(b, off)
        if r is None:
            break
        fwd.append(r)
        off += STRIDE
        if len(fwd) > 20000:
            break
    # 向前读
    back = []
    off = anchor - STRIDE
    while True:
        r = rec_at(b, off)
        if r is None:
            break
        back.append(r)
        off -= STRIDE
        if len(back) > 20000:
            break
    back.reverse()
    rows = back + fwd

    print("向后 %d 条, 向前 %d 条, 合计 %d 条" % (len(fwd), len(back), len(rows)))
    if rows:
        print("sku 范围: %d .. %d" % (min(r["sku"] for r in rows),
                                     max(r["sku"] for r in rows)))
        print("不同 productId: %d" % len(set(r["productId"] for r in rows)))
        print()
        print("前 20 条:")
        for r in rows[:20]:
            print("   sku=%-7d price=%-8d dur=%-5d productId=%d"
                  % (r["sku"], r["price"], r["duration"], r["productId"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "price", "duration", "productId"])
        w.writeheader()
        w.writerows(rows)
    print("\n导出 -> %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
