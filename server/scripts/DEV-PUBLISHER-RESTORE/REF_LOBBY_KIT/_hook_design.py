# -*- coding: utf-8 -*-
"""设计并落地"抓 itemID -> ref 映射"的运行时方案。

已知:
  - 客户端打开军牌定制时, CallSignObj 的 cardBackgroundItemID 等字段会被赋值
  - 我们买到的 item 是 15166 / 22381 / 22384
  - 但内存静态扫不到 ref 与这些 ID 的关联

可行方案(不需要调试器):
  在军牌定制**打开前后**各 dump 一次内存, 对比差异。
  差异区里出现的 ref 字符串 + 附近 u32 = 该 ref 的 itemID。

本脚本: 记录"打开军牌定制前"的内存快照(只存含 callsign ref 的区段),
        之后用 _diff_callsign_snapshots.py 对比。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
OUT = os.path.join(ROOT, "mem_callsign")
REF_RE = re.compile(rb"\b(pcb|pci|pct|pcf|pcab|pcai|pcaf|pcn|cnc|bdg)_[A-Za-z0-9_]{2,60}")


def main():
    os.makedirs(OUT, exist_ok=True)
    tag = sys.argv[1] if len(sys.argv) > 1 else "before"
    n = 0
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        if not REF_RE.search(b):
            continue
        dst = os.path.join(OUT, "%s_%s" % (tag, fn))
        with open(dst, "wb") as f:
            f.write(b)
        n += 1
    print("已快照 %d 个含 callsign ref 的内存区 -> %s (%s)" % (n, OUT, tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
