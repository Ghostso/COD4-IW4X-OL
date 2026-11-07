# -*- coding: utf-8 -*-
"""020: write title + leading conclusion block of every DEV-BOOKING doc to a utf-8 file."""
import os, datetime, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "DEV-BOOKING")
OUT = os.path.join(D, "_gist_tmp.md")
files = sorted(glob.glob(os.path.join(D, "*.md")))
buf = []
for p in files:
    if os.path.basename(p).startswith("_"):
        continue
    try:
        txt = open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    lines = txt.splitlines()
    title = ""
    for ln in lines:
        if ln.strip().startswith("#"):
            title = ln.strip().lstrip("# ").strip()
            break
    out, sep = [], 0
    for ln in lines[1:]:
        if ln.strip() == "---":
            sep += 1
            if sep >= 2:
                break
            continue
        out.append(ln)
        if len(out) >= 24:
            break
    mt = datetime.datetime.fromtimestamp(os.stat(p).st_mtime).strftime("%m-%d %H:%M")
    buf.append("=" * 100)
    buf.append("[%s] %s  | %s" % (mt, os.path.basename(p), title))
    buf.append("\n".join(out).strip()[:900])
open(OUT, "w", encoding="utf-8").write("\n".join(buf))
print("wrote", OUT, len(buf), "lines")
