# -*- coding: utf-8 -*-
"""从 bak_big 恢复完整仓库(但保留刚买的几件 + Priority)。"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(ROOT, "marketplace-inventory.json")
BAK = os.path.join(ROOT, "marketplace-inventory.json.bak_big")


def main():
    if not os.path.exists(BAK):
        print("没有备份, 跳过")
        return 1
    big = json.load(open(BAK, "r", encoding="utf-8"))
    cur = json.load(open(INV, "r", encoding="utf-8"))
    # 把当前(小仓库)里新增的并回大仓库
    merged = dict(big)
    items = dict(big.get("Items", {}))
    for k, v in cur.get("Items", {}).items():
        items.setdefault(k, v)
    merged["Items"] = items
    # Priority 保留当前的, 再加原始 7 件
    pri = list(cur.get("Priority", []))
    for k in ("10007", "26666", "27724", "27725", "27720", "11016", "11722"):
        if k in items and k not in pri:
            pri.append(k)
    merged["Priority"] = pri
    with open(INV, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, separators=(",", ":"))
    print("恢复: %d 件 (小仓库 %d -> 大仓库 %d)"
          % (len(items), len(cur.get("Items", {})), len(big.get("Items", {}))))
    print("Priority: %s" % pri[:15])
    return 0


if __name__ == "__main__":
    sys.exit(main())
