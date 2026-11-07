"""Search every handoff/report for how 'cannot connect to lobby service' was
previously resolved -- especially any IP/address field that had to be fixed.
"""
import glob
import io
import os
import re

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
KEYS = [
    "无法连接大厅服务",
    "无法连接",
    "失去连接",
    "大厅服务",
]

hits = []
for pat in ["CODOLServer/**/*.md", "CODOLServer/*.md"]:
    for f in glob.glob(os.path.join(ROOT, pat), recursive=True):
        if "backup" in f or "archive" in f:
            continue
        try:
            txt = io.open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if any(k in txt for k in KEYS):
            lines = txt.splitlines()
            for i, l in enumerate(lines):
                if any(k in l for k in KEYS):
                    ctx = " / ".join(x.strip() for x in
                                     lines[max(0, i - 1):i + 3] if x.strip())
                    hits.append((os.path.basename(f), i + 1, ctx[:220]))

print("=== %d hits mentioning the lobby-connect failure ===" % len(hits))
seen = set()
for name, ln, ctx in hits:
    key = (name, ctx[:80])
    if key in seen:
        continue
    seen.add(key)
    print()
    print("  %s:%d" % (name, ln))
    print("     ", ctx)
