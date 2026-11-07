"""Hunt the handoff documents for the DEFINITIVE cause+fix of
'[100]无法连接大厅服务', and separate it from the later, different failure
'与大厅服务失去连接' (a dialog, not the rendered [100] text).
"""
import glob
import io
import os
import re

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"

CAUSE_WORDS = ["根因", "原因", "因为", "导致", "修复", "解决", "改成", "改为",
               "填入", "填成", "设为", "写成"]
TARGET = "无法连接大厅服务"

files = []
for pat in ["CODOLServer/**/*.md", "CODOLServer/*.md"]:
    files += glob.glob(os.path.join(ROOT, pat), recursive=True)
files = [f for f in files if "backup" not in f and "archive" not in f]

print("scanned %d documents" % len(files))
print()

for f in sorted(files):
    try:
        txt = io.open(f, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    if TARGET not in txt:
        continue
    lines = txt.splitlines()
    print("=" * 70)
    print(os.path.basename(f))
    print("=" * 70)
    shown = 0
    for i, l in enumerate(lines):
        if TARGET not in l:
            continue
        # print a small window, but only when it adds information
        win = lines[max(0, i - 3): i + 6]
        blob = " ".join(w.strip() for w in win)
        if not any(c in blob for c in CAUSE_WORDS):
            continue
        print("  --- line %d ---" % (i + 1))
        for w in win:
            if w.strip():
                print("     ", w.strip()[:120])
        shown += 1
        if shown >= 3:
            break
    if shown == 0:
        print("   (mentions it, but no cause/fix wording nearby)")
    print()
