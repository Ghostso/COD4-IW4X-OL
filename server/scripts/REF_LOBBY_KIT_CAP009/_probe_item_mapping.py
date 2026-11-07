# -*- coding: utf-8 -*-
"""查清"运行时 SKU 记录"里的物品字段到底怎么来。

已验证: +0x0C 是价格(与 exe 目录 Price 330/331 吻合)。
未解决: 物品 ID 不在记录的 0x60 字节里。

本脚本做三件事:
  1. 把购买帧的原始 payload 打出来, 看帧里是否自带 item id;
  2. 统计记录 +0x14 的取值有多少落在 exe 目录的 Item 集合里;
  3. 对"点击过的 SKU", 用 价格+货币 去 exe 目录里找同价条目, 看能否唯一确定 Item。
"""
import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")
MEM = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
CAT = os.path.join(ROOT, "marketplace-catalog.json")
UNKNOWN = os.path.join(ROOT, "unknown_skus.txt")


def dump_purchase_frames():
    raw = open(TASKS, "rb").read()
    off = 0
    shown = 0
    while off + 6 <= len(raw) and shown < 6:
        svc = raw[off]
        task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) in ((80, 154), (93, 131)):
            print("frame %d/%d len=%d" % (svc, task, len(pl)))
            print("  hex : %s" % pl.hex())
            u32 = []
            for i in range(0, len(pl) - 3, 4):
                u32.append(struct.unpack_from("<I", pl, i)[0])
            print("  u32@4: %s" % u32)
            shown += 1


def collect_runtime():
    b = open(MEM, "rb").read()
    NONE = 0xFFFFFFFF
    recs = {}
    for off in range(0, len(b) - 0x60, 4):
        sku = struct.unpack_from("<I", b, off)[0]
        if not (1 <= sku <= 500000):
            continue
        f = [struct.unpack_from("<I", b, off + k)[0] for k in range(0, 0x60, 4)]
        if f[1] != 0 or f[2] != 0 or f[6] != NONE or f[7] != NONE:
            continue
        if not (1 <= f[3] <= 10000000):
            continue
        recs.setdefault(sku, f)
    return recs


def main():
    print("=" * 72)
    print("1) 购买帧原始 payload")
    print("=" * 72)
    dump_purchase_frames()

    cat = json.load(open(CAT, "r", encoding="utf-8"))
    by_id = {int(e["Id"]): e for e in cat}
    items = set(int(e["Item"]) for e in cat)
    recs = collect_runtime()
    print()
    print("=" * 72)
    print("2) 记录 +0x14 的取值有多少落在 exe.Item 集合")
    print("=" * 72)
    both = sorted(set(recs) & set(by_id))
    print("运行时记录 %d 条, 与 exe 目录重叠 %d 条" % (len(recs), len(both)))
    hit = sum(1 for s in both if recs[s][5] in items)
    print("  +0x14 命中 exe.Item 值域: %d / %d" % (hit, len(both)))
    hit0 = sum(1 for s in both if recs[s][0] in items)
    print("  +0x00 命中 exe.Item 值域: %d / %d" % (hit0, len(both)))

    print()
    print("=" * 72)
    print("3) 点击过的 SKU: 用 价格 去 exe 目录找同价条目")
    print("=" * 72)
    clicked = []
    for line in open(UNKNOWN, "r", encoding="utf-8", errors="replace"):
        m = re.match(r"\s*(\d+)", line)
        if m:
            clicked.append(int(m.group(1)))
    clicked = sorted(set(clicked))
    by_price = {}
    for e in cat:
        by_price.setdefault(int(e["Price"]), []).append(e)
    uniq = multi = none = 0
    for s in clicked:
        r = recs.get(s)
        if not r:
            print("  sku=%-7d 运行时无记录" % s)
            continue
        price = r[3]
        cands = by_price.get(price, [])
        if len(cands) == 1:
            uniq += 1
            e = cands[0]
            print("  sku=%-7d price=%-7d -> 唯一 exe 条目 Item=%d Cur=%d Cat=%d"
                  % (s, price, e["Item"], e["Currency"], e["Category"]))
        elif len(cands) > 1:
            multi += 1
        else:
            none += 1
    print()
    print("唯一匹配 %d, 多义 %d, 无匹配 %d (共 %d)" % (uniq, multi, none, len(clicked)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
