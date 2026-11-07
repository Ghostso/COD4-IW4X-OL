# -*- coding: utf-8 -*-
"""定位 common_mp / ui_mp 的 IFS 包 —— callsign 表就在这里。"""
import os
import sys

def main():
    cands = [
        r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\IIPS\IIPSDownload",
        r"D:\BaiduNetdiskDownload\使命召唤OL\IIPS\IIPSDownload",
    ]
    IIPS = next((c for c in cands if os.path.isdir(c)), None)
    if IIPS is None:
        print("找不到 IIPSDownload")
        return 1
    print("IIPS = %s" % IIPS)
    names = sorted(os.listdir(IIPS))
    print("IIPSDownload: %d 个文件" % len(names))
    print()
    for kw in ("common_mp", "ui_mp", "code_post_gfx", "common_marketplace",
               "common_gametype"):
        hits = [n for n in names if kw in n.lower()]
        print("== %s (%d 个) ==" % (kw, len(hits)))
        for n in hits[:20]:
            p = os.path.join(IIPS, n)
            print("  %-60s %d" % (n, os.path.getsize(p)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
