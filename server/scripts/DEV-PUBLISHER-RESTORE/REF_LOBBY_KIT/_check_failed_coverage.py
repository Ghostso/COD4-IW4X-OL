# -*- coding: utf-8 -*-
"""核对: 用户点失败的那些 SKU, 新的 full 目录覆盖了没。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FAILED = [48, 1981, 1011, 15827, 19621, 31173, 31374, 31819, 41314]


def main():
    cli = {int(e["Id"]): e for e in
           json.load(open(os.path.join(ROOT, "marketplace-catalog-client.json"),
                          "r", encoding="utf-8"))}
    full = {int(e["Id"]): e for e in
            json.load(open(os.path.join(ROOT, "marketplace-catalog-full.json"),
                           "r", encoding="utf-8"))}
    print("client 目录 %d 条, full 目录 %d 条" % (len(cli), len(full)))
    print("full 比 client 多 %d 条" % len(set(full) - set(cli)))
    print()
    print("之前点失败的 SKU:")
    for s in FAILED:
        a = "在 client" if s in cli else "不在 client"
        b = ("在 full" if s in full else "不在 full")
        extra = ""
        if s in full:
            e = full[s]
            extra = "  item=%d Cat=%d price=%d" % (e["Item"], e["Category"], e["Price"])
        print("  %-7d %-12s %-10s%s" % (s, a, b, extra))
    return 0


if __name__ == "__main__":
    sys.exit(main())
