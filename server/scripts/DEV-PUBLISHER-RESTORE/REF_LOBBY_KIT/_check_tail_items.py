# -*- coding: utf-8 -*-
"""核对 public.result 尾部那 13 个非零 ID 在 exe 目录里是什么。

如果它们是 Category=1(外观/名片类), 那这个 tail 就是"名片拥有清单"。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAIL_NZ = [30060, 30059, 30061, 10007, 10028, 10049, 10015, 10042,
           10001, 10028, 10001, 10028]
TAIL_ALL = [0, 30060, 30059, 0, 30061, 10007, 10028, 10007, 10049,
            10015, 10042, 10001, 10028, 10001, 10028]


def main():
    cat = json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                         "r", encoding="utf-8"))
    by_item = {}
    for e in cat:
        by_item.setdefault(int(e["Item"]), []).append(e)

    print("尾部非零 ID 逐个核对:")
    for v in sorted(set(TAIL_NZ)):
        es = by_item.get(v, [])
        if es:
            print("  %-6d -> %s" % (v, [(e["Id"], "Cat%d" % e["Category"],
                                         "CP" if e["Currency"] == 1 else "GP")
                                        for e in es[:4]]))
        else:
            print("  %-6d -> 不在 exe 目录" % v)
    print()
    print("我们买到的 4 件:")
    for v in (15166, 22381, 22384, 29892):
        es = by_item.get(v, [])
        print("  %-6d -> %s" % (v, [(e["Id"], "Cat%d" % e["Category"])
                                    for e in es[:3]] if es else "不在 exe 目录"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
