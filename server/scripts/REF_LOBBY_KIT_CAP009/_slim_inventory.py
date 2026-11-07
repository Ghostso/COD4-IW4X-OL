# -*- coding: utf-8 -*-
"""把库存压到 480KB 以内(约 7700 件), 优先保留"用户会买"的类别。

依据(2026-10-06 实测):
  - 客户端 80/203 要 20000 件, 但单次应答 >480KB 会被重置
  - 截断按 item ID 升序 -> 高 ID 物品(名片/消耗品/加成卡)永远发不出去
  - 所以只能主动缩减仓库

保留优先级:
  1. 用户实际买过/点过的 item
  2. Category 6(消耗品/加成卡/黑市币), 2, 4, 5(稀有类)
  3. Category 1(外观/名片) —— 数量最多, 按 ID 截取
  4. Category 3(武器)

输出: marketplace-inventory.json (原文件备份到 .bak_full)
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(ROOT, "marketplace-inventory.json")
BAK = os.path.join(ROOT, "marketplace-inventory.json.bak_full")
CAT = os.path.join(ROOT, "marketplace-catalog.json")

LIMIT = 7600          # 体量上限(480KB / 62B ≈ 7741, 留余量)
MUST = ["60087", "60088", "60138", "17928", "16339", "22384", "29892",
        "15166", "18481", "22381", "8270",
        "10007", "26666", "27724", "27725", "27720", "11016", "11722"]


def main():
    if not os.path.exists(BAK):
        shutil.copy(INV, BAK)
        print("已备份完整仓库 -> %s" % BAK)
    full = json.load(open(BAK, "r", encoding="utf-8"))
    items = full.get("Items", {})
    print("完整仓库: %d 件" % len(items))

    cat = json.load(open(CAT, "r", encoding="utf-8"))
    item_cat = {}
    for e in cat:
        item_cat.setdefault(str(e["Item"]), int(e["Category"]))

    keep = {}
    # 1) 必留
    for k in MUST:
        if k in items:
            keep[k] = items[k]
    print("必留 %d 件" % len(keep))

    # 2) 按优先级补
    def prio(k):
        c = item_cat.get(k, 0)
        # 稀有类优先(消耗品/加成卡/黑市币等)
        return {6: 0, 2: 1, 4: 2, 5: 3, 1: 4, 0: 5, 3: 6}.get(c, 7)

    rest = [(k, v) for k, v in items.items() if k not in keep]
    rest.sort(key=lambda kv: (prio(kv[0]), int(kv[0])))
    for k, v in rest:
        if len(keep) >= LIMIT:
            break
        keep[k] = v

    # Priority: 必留置顶
    pri = [k for k in MUST if k in keep]
    out = dict(full)
    out["Items"] = keep
    out["Priority"] = pri
    with open(INV, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    from collections import Counter
    print("缩减后: %d 件" % len(keep))
    print("Category 分布:", Counter(item_cat.get(k, -1) for k in keep).most_common())
    print("预估应答: %d 字节 (%.0f KB)"
          % (len(keep) * 62, len(keep) * 62 / 1024.0))
    print("Priority: %s" % pri)
    return 0


if __name__ == "__main__":
    sys.exit(main())
