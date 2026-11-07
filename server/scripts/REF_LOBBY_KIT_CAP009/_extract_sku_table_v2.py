# -*- coding: utf-8 -*-
"""从内存转储里提取**客户端 SKU 运行时表**（SKU -> Item/Price/Days）。

来历（2026-10-07）：
  * 旧 `_extract_client_catalog.py` 只认"用户点过的 SKU"，判据偏松
    （+0x04==0 且 +0x10==0 且 +0x1C 是类型枚举），且遇到歧义就整条丢弃，
    结果只拿到 107 条，且被上一轮误判成"低 Item 是噪声"。
  * 本轮换了个路子：**先拿已实测入库成功的 SKU 做 ground truth**，
    反推出记录布局，再用同一布局全库扫。ground truth 是硬证据：

        37251 -> Item 29892  Price  8000  days 0    (CP)
        31184 -> Item 22384  Price   680  days 7    (GP)
        37116 -> Item 29767  Price 10000  days 0    (CP)
        16096 -> Item  7110  Price   880  days 0    (GP)
        31774 -> Item   122  Price  2280  days 30   (CP, 白名单)

    这 5 条来自 `_verify_merged_purchase.py` / `HANDOFF_20261006_MERGED_CATALOG.md`
    的实测记录，**不是猜的**。

布局（每条记录 4 字节步进，字段相对记录头）：
    +0x00  SKU (u32)
    +0x04  必须为 0（记录标志）
    +0x08  价格（变体 A；另一变体为 0）
    +0x0C  价格（变体 B；另一变体为 0）
    +0x10  时长天数（0=永久；0xFFFFFFFF=永久哨兵）
    +0x14  **Item**（要发的物品 id，与库存 key 同一命名空间 —— 已用 29892/22384 验证）
    +0x28  价格副本（== +0x08 或 +0x0C）

★ 关键校验（自洽 + 消灭噪声）：
    1. +0x04 == 0
    2. +0x28 == +0x08 或 +0x28 == +0x0C（两个价格槽之一与副本一致）
    3. 价格 >= 10（地板价；能杀掉 (item=2, price=1) 这类退化命中）
    4. 0 <= days <= 3650 或 days == 0xFFFFFFFF
    5. 1 <= item <= 60000
  同一 SKU 若仍有多个不同候选 -> 判歧义，整条丢弃（宁缺勿错）。

自检：脚本末尾会用那 5 条 ground truth 反查，必须 5/5 命中且数值一致。

用法：
    python -X utf8 _extract_sku_table_v2.py
    python -X utf8 _extract_sku_table_v2.py <别的 mem_linear 目录或 .bin>
    python -X utf8 _extract_sku_table_v2.py <新转储目录> --out mkt_assets/sku_table_v3.csv
输出：
    mkt_assets/sku_table_v2.csv   (sku,item,price,days) [默认]

合并规则（目录模式）：
  同一 SKU 可能在多个区里都出现；同一个 (item,price,days) 会被计票。
  * 只有 1 种取值        -> 采用
  * 有多种、但最高票唯一且 >= 2 -> 采用最高票（打掉零星误命中）
  * 最高票并列           -> 判歧义，丢弃（宁缺勿错）
"""
import csv
import os
import struct
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MEM = os.path.join(ROOT, "mem_linear",
                           "r_259D0000_06400000.bin")
OUT = os.path.join(ROOT, "mkt_assets", "sku_table_v2.csv")
NONE = 0xFFFFFFFF

# ground truth: 已实测入库成功的 (sku, item, price, days)
GROUND_TRUTH = {
    37251: (29892, 8000, 0),
    31184: (22384, 680, 7),
    37116: (29767, 10000, 0),
    16096: (7110, 880, 0),
    31774: (122, 2280, 30),
}

# ★ 2026-10-07: 实测(已验证的 635 条 + 合并目录)真实售价上限是 99999;
#   更大的值全是 9999999 这类哨兵/噪声。收紧到 99999 能打掉
#   "price=9502720 / 1034240 / 65535" 这类跨区巧合命中。
PRICE_FLOOR = 10
MAX_PRICE = 99999
MAX_ITEM = 60000
MAX_SKU = 60000
MAX_DAYS = 3650


def extract(buf):
    """扫一段内存，返回 {sku: (item, price, days)} 与歧义 SKU 列表。"""
    u = struct.unpack_from
    cand = defaultdict(set)
    n = len(buf)
    for off in range(0, n - 0x60, 4):
        sku = u("<I", buf, off)[0]
        if not (1 <= sku <= MAX_SKU):
            continue
        if u("<I", buf, off + 4)[0] != 0:
            continue
        p08 = u("<I", buf, off + 8)[0]
        p0c = u("<I", buf, off + 0x0C)[0]
        p28 = u("<I", buf, off + 0x28)[0]
        if p28 != p08 and p28 != p0c:           # 价格副本必须对上一个价格槽
            continue
        if not (PRICE_FLOOR <= p28 <= MAX_PRICE):
            continue
        days = u("<I", buf, off + 0x10)[0]
        if days > MAX_DAYS and days != NONE:
            continue
        item = u("<I", buf, off + 0x14)[0]
        if not (1 <= item <= MAX_ITEM):
            continue
        # ★ 2026-10-07: 已验证的 635 条里 **从不出现** sku==item，
        #   也不出现 price==days(非 0)。两条都能打掉跨区巧合命中
        #   （如 256->(256,256,0)、133->(274,412,412)）。
        if item == sku:
            continue
        d0 = 0 if days == NONE else days
        if d0 != 0 and p28 == d0:
            continue
        cand[sku].add((item, p28, 0 if days == NONE else days))
    uniq, ambiguous = {}, {}
    for sku, vals in cand.items():
        if len(vals) == 1:
            uniq[sku] = next(iter(vals))
        else:
            ambiguous[sku] = vals
    return uniq, ambiguous


def main():
    args = [a for a in sys.argv[1:]]
    out_path = OUT
    if "--out" in args:
        i = args.index("--out")
        out_path = args[i + 1]
        del args[i:i + 2]
    src = args[0] if args else DEFAULT_MEM
    if os.path.isdir(src):
        votes = defaultdict(Counter)      # sku -> Counter[(item,price,days)]
        for fn in sorted(os.listdir(src)):
            p = os.path.join(src, fn)
            if os.path.isfile(p) and fn.endswith(".bin"):
                buf = open(p, "rb").read()
                uniq, _amb = extract(buf)
                for k, v in uniq.items():
                    votes[k][v] += 1
                # 该区里判歧义的候选也计入(投票会自然压制)
                for k, vals in _amb.items():
                    for v in vals:
                        votes[k][v] += 1
        uniq, ambiguous, conf = {}, {}, {}
        for k, c in votes.items():
            top = c.most_common()
            if len(top) == 1:
                # 只有一种取值：需要 >=2 票才算 high（跨区一致 = 可信）
                uniq[k] = top[0][0]
                conf[k] = "high" if top[0][1] >= 2 else "low"
            elif top[0][1] >= 2 and top[0][1] > top[1][1]:
                uniq[k] = top[0][0]
                conf[k] = "high"
            else:
                ambiguous[k] = c
    else:
        uniq, ambiguous = extract(open(src, "rb").read())
        conf = {k: "high" for k in uniq}

    print("干净记录 %d 条, 歧义 %d 条" % (len(uniq), len(ambiguous)))

    # ---- ground-truth 自检（不通过就不写出） ----
    bad = []
    for sku, exp in GROUND_TRUTH.items():
        got = uniq.get(sku)
        if got != exp:
            bad.append((sku, exp, got))
    print("ground truth 自检: %d/%d 命中" % (len(GROUND_TRUTH) - len(bad),
                                            len(GROUND_TRUTH)))
    for sku, exp, got in bad:
        print("  ✗ sku %d 期望 %r 实得 %r" % (sku, exp, got))
    if bad:
        print("!! ground truth 未全中, 拒绝写出（布局可能变了）")
        return 2

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    n_high = sum(1 for k in uniq if conf.get(k) == "high")
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["sku", "item", "price", "days", "confidence"])
        for sku in sorted(uniq):
            item, price, days = uniq[sku]
            w.writerow([sku, item, price, days, conf.get(sku, "high")])
    print("写出 %s (%d 条, 其中 high-confidence %d)" % (out_path, len(uniq), n_high))
    return 0


if __name__ == "__main__":
    sys.exit(main())
