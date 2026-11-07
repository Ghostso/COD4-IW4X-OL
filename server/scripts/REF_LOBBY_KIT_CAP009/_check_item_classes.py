# -*- coding: utf-8 -*-
"""核对用户点过但买不成的几类道具: 加成卡/消耗品/高级消耗品/黑市币。

已知前缀(来自 exe 字符串表):
    cnc  -> mp/item_cnc.csv     黑市币/代币 (cnc_token)
    消耗品/高级消耗品 -> 可能在 item_asy / item_cac / item_sup / item_etk 等表
    加成卡 -> item_? 

先看我们目录里这些 item 的 Category 分布, 以及用户实际点过的 SKU。
"""
import json
import os
import re
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    # 1) 从 lobby_tasks.bin 提取所有购买 SKU
    tasks = os.path.join(ROOT, "lobby_tasks.bin")
    skus = set()
    if os.path.exists(tasks):
        raw = open(tasks, "rb").read()
        off = 0
        while off + 6 <= len(raw):
            svc = raw[off]
            task = raw[off + 1]
            ln = struct.unpack_from("<I", raw, off + 2)[0]
            if off + 6 + ln > len(raw):
                break
            pl = raw[off + 6:off + 6 + ln]
            off += 6 + ln
            if (svc, task) not in ((80, 154), (93, 131)):
                continue
            vals = []
            i = 0
            while i < len(pl):
                t = pl[i]; i += 1
                if t in (0x01, 0x03):
                    i += 1
                elif t == 0x06:
                    i += 2
                elif t in (0x07, 0x08):
                    vals.append(struct.unpack_from("<I", pl, i)[0]); i += 4
                elif t in (0x09, 0x0A):
                    i += 8
                elif t == 0x10:
                    j = pl.find(b"\x00", i)
                    if j < 0:
                        break
                    i = j + 1
                elif t == 0x13:
                    if i + 5 > len(pl) or pl[i] != 0x08:
                        break
                    n2 = struct.unpack_from("<I", pl, i + 1)[0]
                    i += 5 + n2
                else:
                    break
            if len(vals) >= 4 and vals[1]:
                skus.add(vals[1])
    print("本轮购买请求 SKU: %s" % sorted(skus))
    print()

    # 2) 看这些 SKU 在目录里的条目
    cat = json.load(open(os.path.join(ROOT, "marketplace-catalog-client.json"),
                         "r", encoding="utf-8"))
    by_id = {int(e["Id"]): e for e in cat}
    print("在客户端目录里的条目:")
    for s in sorted(skus):
        e = by_id.get(s)
        if e:
            print("  sku=%-7d item=%-7d Cat=%d %s price=%d days=%d"
                  % (s, e["Item"], e["Category"],
                     "CP" if e["Currency"] == 1 else "GP",
                     e["Price"], e["SelectedDays"]))
        else:
            print("  sku=%-7d ★不在目录里" % s)
    print()

    # 3) 整个客户端目录的 Category 分布
    exe = json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                         "r", encoding="utf-8"))
    print("exe 目录 Category 分布:",
          Counter(int(e["Category"]) for e in exe).most_common())
    print("客户端目录新增 101 条的 Category 分布:",
          Counter(int(e["Category"]) for e in cat
                  if int(e["Id"]) not in
                  set(int(x["Id"]) for x in exe)).most_common())
    return 0


if __name__ == "__main__":
    sys.exit(main())
