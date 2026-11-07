# -*- coding: utf-8 -*-
"""分析 C# 参考实现成功购买的两笔(sku=22858 GP / 22865 CP)。

它那边客户端认了(库存 8 -> 9)。查这两个 SKU 是什么。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SKUS = (22858, 22865)


def main():
    for name in ("marketplace-catalog.json", "marketplace-catalog-client.json"):
        p = os.path.join(ROOT, name)
        if not os.path.exists(p):
            continue
        cat = json.load(open(p, "r", encoding="utf-8"))
        by_id = {int(e["Id"]): e for e in cat}
        print("== %s ==" % name)
        for s in SKUS:
            e = by_id.get(s)
            print("  sku %-6d -> %s" % (s, e))
        print()
    # C# 那边的 inventory 文件?
    print("找 C# 侧的 inventory/account 文件:")
    for base, dirs, files in os.walk(os.path.dirname(ROOT)):
        dirs[:] = [d for d in dirs if d not in
                   ("mem_linear", "mem_marketplace", "mem_callsign",
                    "mem_sku", "__pycache__", ".git", "IIPSDownload",
                    "工具", "backups", "backup_reverse_engineering")]
        for fn in files:
            if ("inventory" in fn.lower() or "player-account" in fn.lower()) \
                    and fn.endswith(".json"):
                p = os.path.join(base, fn)
                print("  %s (%d)" % (p, os.path.getsize(p)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
