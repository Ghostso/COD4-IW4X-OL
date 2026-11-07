# -*- coding: utf-8 -*-
"""把 marketplace-catalog.json 里的全部道具一次性写进当前角色仓库。

仓库文件 = REF_LOBBY_KIT\marketplace-inventory.json 的 Items 字典 {itemId: 数量}。
本脚本只改 Items, 保留 Owner/Version/Build/Transactions, 因此不会触发
"Invalid marketplace inventory owner/version"。

用法: python -X utf8 REF_LOBBY_KIT\_grant_all_items.py [--dry-run]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marketplace_store as ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    root = os.path.dirname(os.path.abspath(__file__))
    # owner 以现有库存为准
    owner = None
    with open(os.path.join(root, "marketplace-inventory.json"), encoding="utf-8") as f:
        owner = int(json.load(f)["Owner"])

    cat = ms.load_catalog()
    items = sorted({int(s.Item) for s in cat.values() if int(s.Item) > 0})

    st = ms.read_inventory(root, owner)
    before = dict(st["Items"])
    print("catalog SKU = %d, 去重 item = %d" % (len(cat), len(items)))
    print("写入前道具数 = %d" % len(before))
    print("抽样(前 8):", {k: st["Items"][k] for k in list(before)[:8]})

    if a.dry_run:
        print("--dry-run: 不改文件")
        return

    st["Items"] = {str(i): 1 for i in items}
    ms.write_inventory(root, owner, st)

    st2 = ms.read_inventory(root, owner)
    print("写入后道具数 = %d" % len(st2["Items"]))
    print("owner=%d version=%s build=%s" % (st2["Owner"], st2["Version"], st2["Build"]))


if __name__ == "__main__":
    main()
