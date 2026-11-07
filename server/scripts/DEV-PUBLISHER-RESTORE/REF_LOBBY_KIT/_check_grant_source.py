# -*- coding: utf-8 -*-
"""查 _grant_all_items.py 里那 17371 个 item ID 是从哪来的。

如果它们是编的/推断的, 那整个库存体系就是错的 ——
客户端算不出这些 item, 自然"看不见", 买什么都白搭。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    p = os.path.join(ROOT, "_grant_all_items.py")
    if not os.path.exists(p):
        print("缺 %s" % p)
        return 1
    txt = open(p, "r", encoding="utf-8", errors="replace").read()
    print("=== _grant_all_items.py 全文 ===")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
