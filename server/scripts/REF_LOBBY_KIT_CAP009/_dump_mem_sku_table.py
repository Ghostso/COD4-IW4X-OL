# -*- coding: utf-8 -*-
"""把内存里那张 SKU 表**整表**导出来。

布局(实测, 步长 0x60 = 96 字节):
    +0x00 u32 sku           <- 客户端购买帧里发的那个 id
    +0x04 u32 0
    +0x08 u32 0
    +0x0C u32 ?             <- 680 / 980 / 8000
    +0x10 u32 ?             <- 7 / 0 / 0
    +0x14 u32 price         <- 22384 / 16339 / 29892
    +0x18 u32 0xFFFFFFFF    <- -1
    +0x1C u32 0xFFFFFFFF    <- -1

来源: mem_linear/r_259D0000_06400000.bin
输出: mkt_assets/mem_sku_table.csv
"""
import csv
import os
import struct

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
OUT = os.path.join(ROOT, "mkt_assets", "mem_sku_table.csv")
STRIDE = 0x60


def looks_like_record(b, off):
    if off < 0 or off + STRIDE > len(b):
        return False
    sku = struct.unpack_from("<I", b, off)[0]
    a = struct.unpack_from("<I", b, off + 0x18)[0]
    c = struct.unpack_from("<I", b, off + 0x1C)[0]
    return (100 <= sku <= 200000) and a == 0xFFFFFFFF and c == 0xFFFFFFFF


def main():
    if not os.path.exists(SRC):
        print("缺 %s" % SRC)
        return 1
    b = open(SRC, "rb").read()
    print("扫描 %s (%.1f MB)" % (os.path.basename(SRC), len(b) / 1048576.0))
    anchors = [0x40C8CC, 0x4D762C, 0x424E6C]
    found = {}
    for a in anchors:
        off = a
        while looks_like_record(b, off - STRIDE):
            off -= STRIDE
        while looks_like_record(b, off):
            sku = struct.unpack_from("<I", b, off)[0]
            found[sku] = off
            off += STRIDE
    rows = []
    for sku, off in sorted(found.items(), key=lambda kv: kv[1]):
        f = struct.unpack_from("<8I", b, off)
        rows.append({"sku": sku, "off": "0x%08X" % off,
                     "f0C": f[3], "f10": f[4], "price": f[5]})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["sku", "off", "f0C", "f10", "price"])
        w.writeheader()
        w.writerows(rows)
    print("导出 %d 条 -> %s" % (len(rows), OUT))
    for r in rows[:25]:
        print("  sku=%-7d price=%-8d f0C=%-6d f10=%d  @%s"
              % (r["sku"], r["price"], r["f0C"], r["f10"], r["off"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
