#!/usr/bin/env python3
"""138 勘察: 全体 run 的 svc11/21 时间线 —— 找"房间请求消失"的断点。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUNS = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs"
rows = []
for name in sorted(os.listdir(RUNS)):
    for sub in ("kit", "runtime_kit"):
        p = os.path.join(RUNS, name, sub, "lobby_srv.log")
        if not os.path.isfile(p):
            continue
        txt = open(p, encoding="utf-8", errors="replace").read()
        c11 = txt.count("service=11 ver")
        c21 = txt.count("service=21 ver")
        c6 = txt.count("service=6 ver")
        c11_4 = txt.count("service=11 ver=0x03 task=4")
        conn = txt.count("大厅连接建立")
        rows.append((name, c11, c11_4, c21, c6, conn, len(txt)))
rows.sort()
print("%-28s %5s %6s %5s %4s %4s %9s" % ("run", "svc11", "11/4", "svc21", "s6", "conn", "bytes"))
for n, a, a4, b, c, cn, ln in rows:
    if n.startswith("ONCE_20261029") or n.startswith("ONCE_2026103"):
        mark = "  <<< 11/4 出现" if a4 else ""
        print("%-28s %5d %6d %5d %4d %4d %9d%s" % (n, a, a4, b, c, cn, ln, mark))
