# -*- coding: utf-8 -*-
"""做一个"只留外观类(Category=1) + 用户买过的"小仓库, 用于验证名片可见性。

目的: 排除 480KB 截断的干扰。若缩小仓库后名片出现 -> 走仓库;
      若仍不出现 -> 名片走档案/本地表, 与仓库无关。
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(ROOT, "marketplace-inventory.json")
BAK = os.path.join(ROOT, "marketplace-inventory.json.bak_big")
CAT = os.path.join(ROOT, "marketplace-catalog.json")

KEEP_ALWAYS = ["18481", "29892", "22381", "22384", "8270", "16339"]


def main():
    if not os.path.exists(BAK):
        shutil.copy(INV, BAK)
        print("已备份 -> %s" % BAK)
    full = json.load(open(BAK, "r", encoding="utf-8"))
    allitems = full.get("Items", {})

    cat = json.load(open(CAT, "r", encoding="utf-8"))
    item_cat = {}
    for e in cat:
        item_cat.setdefault(int(e["Item"]), set()).add(int(e["Category"]))

    # 只保留 Category=1(外观) 以及买过的
    keep = {}
    for k, v in allitems.items():
        i = int(k)
        if k in KEEP_ALWAYS or (1 in item_cat.get(i, ())):
            keep[k] = v
    # 上限保护: 外观类有 14903 件, 仍可能超预算, 先取前 3000(按 ID)
    if len(keep) > 3000:
        keep_items = sorted(keep.items(), key=lambda kv: int(kv[0]))[:3000]
        keep = dict(keep_items)
    out = dict(full)
    out["Items"] = keep
    out["Priority"] = [k for k in KEEP_ALWAYS if k in keep]
    with open(INV, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("小仓库: %d 件 (原 %d)" % (len(keep), len(allitems)))
    print("Priority: %s" % out["Priority"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
