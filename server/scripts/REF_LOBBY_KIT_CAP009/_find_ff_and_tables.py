# -*- coding: utf-8 -*-
"""找游戏数据文件(.ff)以及里面的 callsign 表。

关键问题: 客户端能在军牌定制里列出名片/徽章/称号, 但我们的目录页是空的。
那这个列表必然来自**游戏自带的数据文件**。
"""
import os
import re
import sys
from collections import Counter

GAME = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"


def main():
    ff = []
    for base, dirs, files in os.walk(GAME):
        for fn in files:
            if fn.lower().endswith((".ff", ".ifs")):
                p = os.path.join(base, fn)
                try:
                    sz = os.path.getsize(p)
                except OSError:
                    sz = -1
                ff.append((os.path.relpath(p, GAME), sz))
    print("游戏目录里 .ff/.ifs 文件: %d 个" % len(ff))
    for p, sz in sorted(ff, key=lambda x: -x[1])[:50]:
        print("  %-72s %d" % (p, sz))
    print()
    # IIPS 下载目录
    iips = os.path.join(os.path.dirname(GAME), "IIPS", "IIPSDownload")
    if not os.path.isdir(iips):
        iips = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\IIPS\IIPSDownload"
    if os.path.isdir(iips):
        names = os.listdir(iips)
        print("IIPSDownload: %d 个文件" % len(names))
        c = Counter()
        for n in names:
            c[os.path.splitext(n)[1].lower()] += 1
        print("  扩展名分布:", c.most_common(12))
        cs = [n for n in names if "callsign" in n.lower() or "badge" in n.lower()]
        print("  含 callsign/badge 的:", cs[:20])
    return 0


if __name__ == "__main__":
    sys.exit(main())
