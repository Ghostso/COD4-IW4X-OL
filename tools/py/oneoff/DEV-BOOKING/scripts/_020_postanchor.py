# -*- coding: utf-8 -*-
"""020: list all docs modified after the lobby anchor (2026-10-05 16:36)."""
import os, re, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CUT = datetime.datetime(2026, 10, 5, 16, 36).timestamp()
SKIP = re.compile(r"\\backups\\|\\archive\\|\\node_modules\\|\\debuggercmds?\\|"
                  r"\\工具\\|\\WeGame|\\COD OL\\|\\run_codol_001\\|\\REF_LOBBY_KIT\\|"
                  r"\\DEV-PUBLISHER-RESTORE\\|\\backup_reverse_engineering\\")
rows = []
for dp, dn, fn in os.walk(ROOT):
    if SKIP.search(dp + "\\"):
        continue
    for f in fn:
        if not f.lower().endswith((".md", ".txt")):
            continue
        p = os.path.join(dp, f)
        try:
            st = os.stat(p)
        except Exception:
            continue
        if st.st_mtime <= CUT or st.st_size > 4_000_000:
            continue
        try:
            head = open(p, encoding="utf-8", errors="replace").read(3000)
        except Exception:
            continue
        first = ""
        for ln in head.splitlines():
            ln = ln.strip()
            if ln.startswith("#"):
                first = ln.lstrip("# ").strip()
                break
        rows.append((st.st_mtime, os.path.relpath(p, ROOT), first[:64], st.st_size))
rows.sort()
print("=== post-anchor docs (outside big/dup dirs): %d ===" % len(rows))
last = ""
for m, rel, first, sz in rows:
    d = datetime.datetime.fromtimestamp(m).strftime("%m-%d %H:%M")
    print("%s | %-58s | %s" % (d, rel[:58], first))
