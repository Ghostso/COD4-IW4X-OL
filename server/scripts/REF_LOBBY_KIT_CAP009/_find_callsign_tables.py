# -*- coding: utf-8 -*-
"""在游戏目录里找 Callsign 相关表(callsignTitle.csv / badgeTable.csv 等)。

已知(交接文档): 这些是文本表, 不在 marketplace 包里。
"""
import os
import re
import sys

GAME = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
PAT = re.compile(r"callsign|badge|emblem|nameplate|title", re.I)
SKIP = {"mem_linear", "mem_marketplace", "mem_callsign", "mem_sku",
        "mkt_assets", "__pycache__", ".git", "Logs"}


def main():
    hits = []
    for base, dirs, files in os.walk(GAME):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for fn in files:
            if PAT.search(fn):
                p = os.path.join(base, fn)
                try:
                    sz = os.path.getsize(p)
                except OSError:
                    sz = -1
                hits.append((os.path.relpath(p, GAME), sz))
    print("文件名命中 %d 个:" % len(hits))
    for p, sz in sorted(hits)[:120]:
        print("  %-70s %d" % (p, sz))
    return 0


if __name__ == "__main__":
    sys.exit(main())
