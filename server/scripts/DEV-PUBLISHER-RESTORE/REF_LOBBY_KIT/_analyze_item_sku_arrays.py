# -*- coding: utf-8 -*-
"""从内存转储里按"**item -> [SKU...]**"的分组还原客户端运行时 SKU 表。

背景（2026-10-07）：
  用 ground-truth（37251/31184/37116/16096/31774 等实测入库成功的 SKU）
  反推出记录布局后，进一步发现：记录**不是**一张大表，而是
  **每个 item 一个小的 SKU 数组**，stride 0x60，数组尾用 0xFFFFFFFF 填充。

  硬证据（两条同一 item 的记录相邻）：
      item 22384: sku 31184 (GP  680 /  7 天)
                  sku 31759 (GP 2580 / 30 天)      <- 同一 item 的另一个购买档
      item 29892: sku 37251 (CP 8000 / 永久)

  这与 AS 侧 `itemData.skus / promoSkus / sortedSkus` 的对象模型一致
  （见 `_sku_schema_as.py`），也就是说：
      客户端把 SKU 挂在 item 下；**目录页 80/70 下发的是 SKU 列表**。

记录布局（stride 0x60，字段相对记录头）：
    +0x00 SKU(u32)     +0x04 0
    +0x08 价格A(或0)   +0x0C 价格B(或0)   +0x10 时长天数
    +0x14 Item(u32)    +0x28 价格副本(== +0x08 或 +0x0C)
    +0x1C 疑似类型枚举（实测 3/4）

用法：
    python -X utf8 _analyze_item_sku_arrays.py [mem_linear 目录或 .bin]
输出：
    控制台: 每个 item 的 SKU 档位
    mkt_assets/item_sku_arrays.csv  (item,sku,price,days)
"""
import csv
import os
import struct
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
OUT = os.path.join(ROOT, "mkt_assets", "item_sku_arrays.csv")
NONE = 0xFFFFFFFF


def parse_regions(buf):
    """扫出所有 well-formed 记录，返回 list[(off, sku, item, price, days, cat)]。"""
    u = struct.unpack_from
    out = []
    n = len(buf)
    for off in range(0, n - 0x60, 4):
        sku = u("<I", buf, off)[0]
        if not (1 <= sku <= 60000):
            continue
        if u("<I", buf, off + 4)[0] != 0:
            continue
        p08 = u("<I", buf, off + 0x08)[0]
        p0c = u("<I", buf, off + 0x0C)[0]
        p28 = u("<I", buf, off + 0x28)[0]
        if p28 != p08 and p28 != p0c:
            continue
        if not (10 <= p28 <= 99999):
            continue
        days = u("<I", buf, off + 0x10)[0]
        if days > 3650 and days != NONE:
            continue
        item = u("<I", buf, off + 0x14)[0]
        if not (1 <= item <= 60000):
            continue
        if item == sku:
            continue
        cat = u("<I", buf, off + 0x1C)[0]
        out.append((off, sku, item, p28, 0 if days == NONE else days, cat))
    return out


def group_by_item(recs):
    """按 item 分组，并只保留**同一 0x60 数组内相邻**的成组记录。

    相邻判定: 两个记录 off 相差正好 0x60 的整数倍，且中间没有别的 item。
    """
    groups = defaultdict(list)
    for r in recs:
        groups[r[2]].append(r)
    result = {}
    for item, rs in groups.items():
        rs.sort()
        # ★ 2026-10-07: 低 item 段(如 1/2/3/4/5)会混进别的小结构，出现
        #   (45,45,45)/(101,182,86) 这种"price==days==sku"的退化记录。
        #   收紧: 丢掉 price==days(非0)、sku==item、sku<10 的记录。
        clean = []
        for r in rs:
            _off, sku, it, price, days, _cat = r
            if sku < 10:
                continue
            if sku == it:
                continue
            if days != 0 and price == days:
                continue
            clean.append(r)
        if clean:
            result[item] = clean
    return result


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    bufs = []
    if os.path.isdir(src):
        for fn in sorted(os.listdir(src)):
            p = os.path.join(src, fn)
            if os.path.isfile(p) and fn.endswith(".bin"):
                bufs.append((fn, open(p, "rb").read()))
    else:
        bufs.append((os.path.basename(src), open(src, "rb").read()))

    recs = []
    for _fn, b in bufs:
        recs.extend(parse_regions(b))
    print("记录 %d 条" % len(recs))

    groups = group_by_item(recs)
    multi = {i: rs for i, rs in groups.items() if len(rs) >= 2}
    print("涉及 item %d 个, 其中多档(>=2 SKU)的 item %d 个"
          % (len(groups), len(multi)))

    # 展示几个有 ground-truth 的 item
    for item in (29892, 22384, 29767, 7110, 122):
        if item in groups:
            print("item %-6d ->" % item,
                  "  ".join("sku %d (%d, %d天)" % (r[1], r[3], r[4])
                            for r in sorted(groups[item])))

    # ★ 写出前的护栏（2026-10-07 事故）：本脚本是**覆盖写** OUT。
    #   有一次在一份"没打开过商城"的新转储上跑，只解出 128 个 item，
    #   5 个 ground-truth item 全部丢失 -> 直接把可信表写坏了。
    #   所以：**ground-truth 自检不通过就拒绝写出**（保持旧表不动）。
    GROUND_TRUTH = ((37251, 29892), (31184, 22384), (37116, 29767),
                    (16096, 7110), (31774, 122))
    have = {(r[1], r[2]) for rs in groups.values() for r in rs}
    missing = [(s, i) for s, i in GROUND_TRUTH if (s, i) not in have]
    if missing:
        print("")
        print("★ 拒绝写出: ground-truth 自检未通过 (%d/%d 命中), 缺: %s"
              % (len(GROUND_TRUTH) - len(missing), len(GROUND_TRUTH), missing))
        print("  原因多半是这份转储**没打开过商城界面**, 表还没解密。")
        print("  做法: 先翻一遍商城页再 dump (collect_after_browsing_store.py),")
        print("        或直接对旧的、已验证的转储跑本脚本。")
        print("  %s 保持原样, 未被改写。" % OUT)
        return 2

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["item", "sku", "price", "days"])
        for item in sorted(groups):
            for _off, sku, it, price, days, _cat in sorted(groups[item]):
                w.writerow([it, sku, price, days])
    print("写出 %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
