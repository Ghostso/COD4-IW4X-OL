# -*- coding: utf-8 -*-
"""看 C# 侧的落盘文件: Purchase 到底有没有真写库存。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    d = os.path.join(os.path.dirname(ROOT), "CODOLServer", "lobby_server", "data")
    if not os.path.isdir(d):
        print("缺 %s" % d)
        return 1
    print("== %s ==" % d)
    for fn in sorted(os.listdir(d)):
        p = os.path.join(d, fn)
        if not os.path.isfile(p):
            continue
        print("  %-40s %d 字节" % (fn, os.path.getsize(p)))
        if fn.endswith(".json"):
            try:
                j = json.load(open(p, "r", encoding="utf-8"))
                if isinstance(j, dict) and "Items" in j:
                    print("      Items=%d, Transactions=%d"
                          % (len(j["Items"]), len(j.get("Transactions", []))))
            except Exception as e:
                print("      (解析失败 %r)" % (e,))
    return 0


if __name__ == "__main__":
    sys.exit(main())
