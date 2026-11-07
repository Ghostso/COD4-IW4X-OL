# -*- coding: utf-8 -*-
"""重新分析 callsign_0x71B40000.bin —— 里面 723 个 TITLE_ 可能真是称号表。

同时搜 pcb_/pci_/pct_/bdg_/cnc_ 前缀, 判断是"表数据"还是"本地化文本"。
"""
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(ROOT, "mem_callsign", "callsign_0x71B40000.bin")


def main():
    b = open(CAP, "rb").read()
    print("文件 %d 字节" % len(b))
    print()
    for pre in (b"TITLE_", b"SUBTITLE_", b"pcb_", b"pci_", b"pct_", b"bdg_",
                b"cnc_", b"PCI_", b"PCB_", b"PCT_", b"BDG_"):
        print("  %-12s %d 次" % (pre.decode(), b.count(pre)))
    print()

    # 提取所有 TITLE_ 开头的串
    titles = sorted(set(
        m.group(0).decode("latin1")
        for m in re.finditer(rb"TITLE_[A-Za-z0-9_]{4,80}", b)))
    print("TITLE_ 唯一串 %d 个, 前 50:" % len(titles))
    for t in titles[:50]:
        print("  %s" % t)
    print()
    # 有没有看起来像 CSV 表头的
    for kw in (b"ref,", b"name,", b"ref\t", b"unlockRank", b"killsReq",
               b"isOnlyTryon", b"exclusiveList", b"primaryValKeyArray",
               b"baseID", b"parentName"):
        print("  %-22s %d 次" % (kw.decode(), b.count(kw)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
