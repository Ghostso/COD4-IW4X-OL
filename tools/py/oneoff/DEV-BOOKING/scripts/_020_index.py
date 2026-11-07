# -*- coding: utf-8 -*-
"""020: build a compact index of project docs, and grep for lobby-entry milestones."""
import os, re, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEYS = ["进大厅", "进入大厅", "能进大厅", "大厅 UI", "Online Lobby", "首次进大厅",
        "登录成功", "进入正式大厅", "lobby entered", "LOBBY OK"]
SKIP = re.compile(r"\\backups\\|\\archive\\|\\node_modules\\|\\debuggercmds?\\|\\工具\\|\\WeGame")
rows = []
for dp, dn, fn in os.walk(ROOT):
    if SKIP.search(dp):
        continue
    for f in fn:
        if not f.lower().endswith((".md", ".txt")):
            continue
        p = os.path.join(dp, f)
        try:
            st = os.stat(p)
        except Exception:
            continue
        if st.st_size > 3_000_000:
            continue
        try:
            head = open(p, encoding="utf-8", errors="replace").read(4000)
        except Exception:
            continue
        first = ""
        for ln in head.splitlines():
            ln = ln.strip()
            if ln.startswith("#"):
                first = ln.lstrip("# ").strip()
                break
        hits = [k for k in KEYS if k in head]
        rows.append((st.st_mtime, os.path.relpath(p, ROOT), first[:70], st.st_size, hits))
rows.sort()
print("=== docs containing lobby-entry milestone keywords (time-ordered) ===")
for m, rel, first, sz, hits in rows:
    if hits:
        print("%s | %-62s | %s | %s" % (datetime.datetime.fromtimestamp(m).strftime("%Y-%m-%d %H:%M"), rel[:62], ",".join(hits), first[:34]))
print()
print("total md/txt docs indexed = %d" % len(rows))
