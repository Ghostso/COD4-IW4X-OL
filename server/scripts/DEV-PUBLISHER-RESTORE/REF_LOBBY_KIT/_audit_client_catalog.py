# -*- coding: utf-8 -*-
"""审计 client_catalog.csv: 每个 SKU 的候选记录是否有冲突。

干净记录有两种价格变体:
  变体 A: +08=price, +0C=0
  变体 B: +0C=price, +08=0
两者都要求 +04=0, +10=days(0..3650), +14=item(1..500000), price>=10。

输出每个 SKU 的候选 (price,item) 分布; 有多个不同取值的标为冲突。
"""
import csv
import os
import struct
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
CSV = os.path.join(ROOT, "mkt_assets", "client_catalog.csv")
NONE = 0xFFFFFFFF
STRIDE = 0x60


def main():
    rows = list(csv.DictReader(open(CSV, "r", encoding="utf-8-sig")))
    targets = {int(r["sku"]): (int(r["price"]), int(r["item"]), int(r["days"]))
               for r in rows}

    b = open(MAIN, "rb").read()
    cand = defaultdict(Counter)
    for off in range(0, len(b) - STRIDE, 4):
        sku = struct.unpack_from("<I", b, off)[0]
        if sku not in targets:
            continue
        f04 = struct.unpack_from("<I", b, off + 4)[0]
        f08 = struct.unpack_from("<I", b, off + 8)[0]
        f0c = struct.unpack_from("<I", b, off + 0xC)[0]
        f10 = struct.unpack_from("<I", b, off + 0x10)[0]
        item = struct.unpack_from("<I", b, off + 0x14)[0]
        f1c = struct.unpack_from("<I", b, off + 0x1C)[0]
        if f04 != 0:
            continue
        # +0x1C 是类型枚举: 实测取值 -1/1/2/4/12, 接受 -1 或 0..15
        if f1c != NONE and not (0 <= f1c <= 15):
            continue
        if f10 > 3650:
            continue
        if not (1 <= item <= 500000):
            continue
        price = f0c if 10 <= f0c <= 10000000 else 0
        if price == 0 and 10 <= f08 <= 10000000:
            price = f08
        if price == 0:
            continue
        cand[sku][(price, item, f10)] += 1

    conflict = 0
    missing = 0
    for sku in sorted(targets):
        want = targets[sku]
        c = cand.get(sku, Counter())
        if not c:
            missing += 1
            print("MISSING  sku=%-7d want=%s" % (sku, want))
            continue
        if len(c) > 1:
            conflict += 1
            print("CONFLICT sku=%-7d want=%s  all=%s"
                  % (sku, want, c.most_common(4)))
        elif c.most_common(1)[0][0] != want:
            conflict += 1
            print("MISMATCH sku=%-7d want=%s  got=%s"
                  % (sku, want, c.most_common(1)[0][0]))

    print()
    print("共 %d 条: 冲突/不符 %d, 缺失 %d, 干净 %d"
          % (len(targets), conflict, missing, len(targets) - conflict - missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
