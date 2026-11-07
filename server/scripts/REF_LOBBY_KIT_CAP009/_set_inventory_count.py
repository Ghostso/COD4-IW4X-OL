# -*- coding: utf-8 -*-
"""把角色仓库设成 catalog 里前 N 个道具(用于二分定位客户端单次应答上限)。

用法: python -X utf8 _set_inventory_count.py 2000
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marketplace_store as ms


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    root = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(root, "marketplace-inventory.json"), encoding="utf-8") as f:
        owner = int(json.load(f)["Owner"])
    items = sorted({int(s.Item) for s in ms.load_catalog().values() if int(s.Item) > 0})[:n]
    st = ms.read_inventory(root, owner)
    st["Items"] = {str(i): 1 for i in items}
    ms.write_inventory(root, owner, st)
    d = ms.marketplace_player_data(root, owner)
    print("设为 %d 件; 80/230 应答 = %d 字节" % (len(items), len(d)))


if __name__ == "__main__":
    main()
