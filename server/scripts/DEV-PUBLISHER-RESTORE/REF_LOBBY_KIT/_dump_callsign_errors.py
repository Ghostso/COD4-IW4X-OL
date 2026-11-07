# -*- coding: utf-8 -*-
"""找日志里与名片/购买失败相关的客户端报错(UIException 等)。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")


def main():
    txt = open(LOG, "r", encoding="utf-8", errors="replace").read()
    for kw in ("UIException", "Exception", "callsign", "CallSign",
               "card", "nameplate", "title", "购买"):
        n = len(re.findall(re.escape(kw), txt, re.I))
        print("%-14s %d 次" % (kw, n))
    print()
    # 打印所有 UIException 行
    lines = txt.splitlines()
    idx = [i for i, l in enumerate(lines) if "UIException" in l]
    print("UIException 行数: %d" % len(idx))
    for i in idx[-10:]:
        print("  %s" % lines[i][:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
