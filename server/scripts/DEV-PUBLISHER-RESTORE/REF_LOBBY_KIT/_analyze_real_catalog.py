# -*- coding: utf-8 -*-
"""定位客户端真实商品表里的字段布局(不再靠猜)。

做法:
  1. 在 mem_linear 里按 0x60 步长收集候选记录。
  2. 用 exe 内嵌目录(marketplace-catalog.json)做**交叉验证**:
     - 某个偏移上的值若大面积等于 exe.Price -> 那是价格字段
     - 某个偏移上的值若大面积等于 exe.Item  -> 那是物品字段
  3. 打印原始记录, 供人工核对。

只输出结论, 不修改任何数据。
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
CAT = os.path.join(ROOT, "marketplace-catalog.json")
STRIDE = 0x60
NWORDS = STRIDE // 4
NONE = 0xFFFFFFFF


def load_exe_catalog():
    raw = json.load(open(CAT, "r", encoding="utf-8"))
    return {int(e.get("Id", 0)): e for e in raw}


def collect_records():
    """返回 {sku: [24 个 u32]}。

    宽松收集: 只要 +0x00 是合理 sku, +0x0C 是合理价格。
    后续再用 exe 目录交叉验证, 不在这里硬卡字段。
    """
    recs = {}
    files = 0
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        files += 1
        limit = len(b) - STRIDE
        off = 0
        while off <= limit:
            sku = struct.unpack_from("<I", b, off)[0]
            if 1 <= sku <= 500000:
                w = struct.unpack_from("<%dI" % NWORDS, b, off)
                price = w[3]
                if 1 <= price <= 10000000 and w[1] == 0 and w[2] == 0:
                    old = recs.get(sku)
                    if old is None:
                        recs[sku] = list(w)
            off += 4
    return recs, files


def main():
    exe = load_exe_catalog()
    recs, files = collect_records()
    print("扫描 %d 个内存区, 候选记录 %d 条 (0x60 步长)" % (files, len(recs)))

    both = sorted(set(recs) & set(exe))
    print("与 exe 目录重叠的 sku: %d" % len(both))
    if not both:
        print("没有重叠, 无法交叉验证")
        return 1

    print()
    print("偏移   ==exe.Price  ==exe.Item   说明")
    for i in range(NWORDS):
        ep = sum(1 for s in both if recs[s][i] == int(exe[s].get("Price", -1)))
        ei = sum(1 for s in both if recs[s][i] == int(exe[s].get("Item", -1)))
        if ep > len(both) * 0.2 or ei > len(both) * 0.2:
            print("+0x%02X  %-12d %-12d" % (i * 4, ep, ei))

    # 打印原始记录样本
    print()
    print("原始记录样本 (sku, +0x04..+0x5C):")
    for s in both[:12]:
        print("  sku=%-7d %s" % (s, " ".join("%08X" % v for v in recs[s])))
        print("    exe: Item=%-7d Price=%-7d Cur=%s Cat=%s"
              % (exe[s]["Item"], exe[s]["Price"], exe[s]["Currency"], exe[s]["Category"]))

    # 找出 exe.Item 到底落在哪: 对每条记录搜索 Item 值
    print()
    print("exe.Item 在记录中的偏移分布(只统计重叠 sku):")
    from collections import Counter
    dist = Counter()
    for s in both:
        item = int(exe[s]["Item"])
        hits = [i * 4 for i, v in enumerate(recs[s]) if v == item]
        for h in hits:
            dist[h] += 1
    for off, n in sorted(dist.items()):
        print("  +0x%02X : %d" % (off, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
