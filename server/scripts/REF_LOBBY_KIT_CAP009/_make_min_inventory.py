# -*- coding: utf-8 -*-
"""做一个"最小库存"用于验证: 名片/徽章是不是因为库存太大而被截断。

保留: Version/Build/Owner/Transactions + 用户买过的那几件 + Priority。
备份原文件到 marketplace-inventory.json.bak_big
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(ROOT, "marketplace-inventory.json")
BAK = os.path.join(ROOT, "marketplace-inventory.json.bak_big")

KEEP = ["18481", "29892", "22381", "22384"]


def main():
    if not os.path.exists(BAK):
        shutil.copy(INV, BAK)
        print("已备份 -> %s" % BAK)
    inv = json.load(open(BAK, "r", encoding="utf-8"))
    items = inv.get("Items", {})
    new = {k: items[k] for k in KEEP if k in items}
    inv["Items"] = new
    inv["Priority"] = [k for k in KEEP if k in new]
    with open(INV, "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, separators=(",", ":"))
    print("最小库存: %d 件 -> %s" % (len(new), list(new)))
    print("(原 %d 件已备份)" % len(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
