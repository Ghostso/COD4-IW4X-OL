# -*- coding: utf-8 -*-
"""从内存转储里提取"客户端当前目录"的 (SKU, Price, Item)。

已验证的字段含义(2026-10-06, 已被一次真实购买证实):
  +0x00  SKU
  +0x08  价格(变体 A)
  +0x0C  价格(变体 B; 与 exe 目录 Price 330/336 吻合)
  +0x10  时长(天; 0 = 永久)
  +0x14  物品 ID
  +0x1C  类型枚举

★ 硬证据: 实测购买 sku=37251 成功, 库存里出现的 key 正是本条记录的 +0x14(29892)。
  同一条记录里 +0x08=8000 是扣掉的 CP, +0x1C=4 是类型。

物品 ID 的判据(硬证据, 不是猜):
  连续的 SKU 对应连续的 Item, 例如
    37115->29766  37116->29767  37117->29768  37118->29769
    28845->20468  28847->20469  28849->20470
    17274->10033  17276->10034  17278->10035  17282->10037
  这正是物品 ID 枚举的特征。

输出: mkt_assets/client_catalog.csv

★ 2026-10-06 收紧: 全库扫描会产生 11 万条噪声(0x60 步长下大量随机对齐),
  因此只保留**可信子集**:
    - 用户实际点过的 SKU (unknown_skus.txt)
    - 连号样本 (SKU 连号且 Item 也连号, 见 SERIAL)
  这样导出的每一条都有人工可核对的依据。
"""
import csv
import os
import struct
import sys
from collections import Counter, defaultdict

import re

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
MAIN = os.path.join(MEMDIR, "r_259D0000_06400000.bin")
UNKNOWN = os.path.join(ROOT, "unknown_skus.txt")
OUT = os.path.join(ROOT, "mkt_assets", "client_catalog.csv")
NONE = 0xFFFFFFFF
STRIDE = 0x60

# 连号样本: SKU 连号, Item 也连号 —— 可人工核对
SERIAL = (37115, 37116, 37117, 37118,
          28845, 28847, 28849,
          17272, 17274, 17276, 17278, 17280, 17282,
          16350, 19428, 31184, 39592)


def wanted_skus():
    out = set(SERIAL)
    for line in open(UNKNOWN, "r", encoding="utf-8", errors="replace"):
        m = re.match(r"\s*(\d+)", line)
        if m:
            out.add(int(m.group(1)))
    return out


def collect():
    """只扫主区, 且只保留 wanted SKU 的干净记录。"""
    wanted = wanted_skus()
    acc = defaultdict(Counter)
    b = open(MAIN, "rb").read()
    for off in range(0, len(b) - STRIDE, 4):
        sku = struct.unpack_from("<I", b, off)[0]
        if sku not in wanted:
            continue
        f04 = struct.unpack_from("<I", b, off + 4)[0]
        f08 = struct.unpack_from("<I", b, off + 8)[0]
        f0c = struct.unpack_from("<I", b, off + 0xC)[0]
        f10 = struct.unpack_from("<I", b, off + 0x10)[0]
        item = struct.unpack_from("<I", b, off + 0x14)[0]
        f1c = struct.unpack_from("<I", b, off + 0x1C)[0]
        if f04 != 0:
            continue
        # +0x1C 是类型枚举: 实测 -1/1/2/4/12, 接受 -1 或 0..15
        if f1c != NONE and not (0 <= f1c <= 15):
            continue
        # 时长(天): 0 = 永久, 上限取 3650(10 年)
        if f10 > 3650:
            continue
        if not (1 <= item <= 500000):
            continue
        # ★ 下界 10: 实测合法价格最低是 14(992/993), price=1 之类的都是
        #   退化误报(见 _dump_clicked_records.py 里 58/73 的原始记录)。
        price = f0c if 10 <= f0c <= 10000000 else 0
        if price == 0 and 10 <= f08 <= 10000000:
            price = f08
        if price == 0:
            continue
        acc[sku][(price, item, f10)] += 1
    return acc, len(wanted)


def main():
    acc, want = collect()
    print("目标 SKU %d 个, 命中 %d 个" % (want, len(acc)))

    rows = []
    dropped = []
    for sku in sorted(acc):
        # ★ 歧义保护(硬规则): 同一 SKU 若出现**多个不同的物品 ID**,
        #   说明候选里混进了噪声(见 58/73/992/993 的原始记录),
        #   整条丢弃, 宁可不发也不猜。
        items_seen = set(k[1] for k in acc[sku])
        if len(items_seen) > 1:
            dropped.append(sku)
            continue
        (price, item, days), votes = acc[sku].most_common(1)[0]
        rows.append({"sku": sku, "price": price, "item": item,
                     "days": days, "votes": votes})

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "price", "item", "days", "votes"])
        w.writeheader()
        w.writerows(rows)
    print("导出 %d 条 -> %s" % (len(rows), OUT))
    if dropped:
        print("因物品 ID 冲突剔除 %d 条: %s" % (len(dropped), dropped))

    # 自检: 连号组
    print()
    print("连号自检(应看到 Item 也连号):")
    for group in ((37115, 37116, 37117, 37118),
                  (28845, 28847, 28849),
                  (17274, 17276, 17278, 17282),
                  (16350, 19428, 31184, 39592)):
        print("  " + "  ".join(
            "%d->%s" % (s, acc[s].most_common(1)[0][0][1] if s in acc else "?")
            for s in group))
    return 0


if __name__ == "__main__":
    sys.exit(main())
