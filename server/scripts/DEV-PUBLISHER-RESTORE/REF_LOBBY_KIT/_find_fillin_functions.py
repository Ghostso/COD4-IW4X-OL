# -*- coding: utf-8 -*-
"""找"把库存填进 UI 条目"的函数族 —— 武器的叫 WL_FillInInventoryProductItems。

用户实测: 武器能买, 道具/名片不能。
=> 武器的填充路径(WL_*)工作, 非武器的填充路径可能没走到, 或读别的数据。
目标: 找出非武器那一条路径的函数名。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
PATS = [rb"[A-Za-z_]{2,40}FillIn[A-Za-z_]{0,50}",
        rb"[A-Za-z_]{2,40}Inventory[A-Za-z_]{0,50}",
        rb"[A-Za-z_]{2,40}ProductItem[A-Za-z_]{0,40}",
        rb"MKT_[A-Za-z_]{3,50}"]


def main():
    seen = set()
    for fn in sorted(os.listdir(MEM)):
        p = os.path.join(MEM, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for pat in PATS:
            for m in re.finditer(pat, b):
                s = m.group(0).decode("latin1")
                seen.add(s)
    print("总唯一名字 %d 个" % len(seen))
    print()
    for pre in ("FillIn", "Inventory", "ProductItem", "MKT_"):
        hits = sorted(s for s in seen if pre in s)
        print("== 含 %s (%d 个) ==" % (pre, len(hits)))
        for s in hits[:60]:
            print("  %s" % s)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
