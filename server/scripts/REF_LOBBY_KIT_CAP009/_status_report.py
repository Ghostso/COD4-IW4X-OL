# -*- coding: utf-8 -*-
"""当前状态总览(只读)。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def count(p):
    try:
        d = json.load(open(p, "r", encoding="utf-8"))
        if isinstance(d, list):
            return "%d 条" % len(d)
        if isinstance(d, dict) and "Items" in d:
            return "%d 件" % len(d["Items"])
        return "?"
    except Exception as e:
        return "(读取失败)"


def main():
    print("=" * 72)
    print("目录")
    print("=" * 72)
    for f in sorted(os.listdir(ROOT)):
        if f.startswith("marketplace-catalog") and f.endswith(".json"):
            print("  %-52s %s" % (f, count(os.path.join(ROOT, f))))
    print()
    print("=" * 72)
    print("库存")
    print("=" * 72)
    for f in sorted(os.listdir(ROOT)):
        if f.startswith("marketplace-inventory.json"):
            print("  %-56s %s" % (f, count(os.path.join(ROOT, f))))
    print()
    print("=" * 72)
    print("开关 / 标志文件(应尽量为空)")
    print("=" * 72)
    for f in sorted(os.listdir(ROOT)):
        if f.endswith((".on", ".flag")):
            print("  %s" % f)
    print()
    print("=" * 72)
    print("本轮新增的关键文档")
    print("=" * 72)
    for f in sorted(os.listdir(ROOT)):
        if f.startswith("HANDOFF_20261006"):
            print("  %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
