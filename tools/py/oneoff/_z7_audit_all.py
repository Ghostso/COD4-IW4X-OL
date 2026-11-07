"""Rebuild the project state from RAW RUN DATA, not from my own prose.

Every claim is recomputed from run_codol_001/runs/*/aboprobe.stdout so the
result does not depend on anything I wrote earlier (much of which was
retracted).  Output: what is actually reproducible.
"""
import glob
import io
import os
import re
from collections import Counter, defaultdict

RUNS = r"run_codol_001\runs"


def runs():
    out = []
    for d in sorted(glob.glob(os.path.join(RUNS, "IFS1_*")),
                    key=os.path.getmtime):
        f = os.path.join(d, "aboprobe.stdout")
        if not os.path.exists(f):
            continue
        try:
            txt = io.open(f, encoding="gbk", errors="replace").read()
        except Exception:
            continue
        lm = re.search(r"lifetime=([\d.]+)", txt)
        life = float(lm.group(1)) if lm else 0.0
        ex = re.search(r"exitcode=(\S+?),", txt)
        out.append({
            "name": os.path.basename(d),
            "life": life,
            "exit": ex.group(1) if ex else "?",
            "txt": txt,
            "ev": Counter(re.findall(r",([A-Z0-9_]+),", txt)),
        })
    return out


R = runs()
ok = [r for r in R if r["life"] >= 60]
print("=== CORPUS ===")
print("  total runs        : %d" % len(R))
print("  valid (life>=60s) : %d" % len(ok))
print()

print("=== 1. what EVERY valid run achieves (reproducible capability) ===")
keys = ["LOBBY_READY_ONLY", "LOBBY_5E8_READY", "LOBBY_ECHO_READY",
        "SET_P608_DECODED", "LOBBY_SESSION_READY", "POST83_SAMPLE"]
for k in keys:
    n = sum(1 for r in ok if r["ev"].get(k))
    print("  %-22s in %3d/%d valid runs" % (k, n, len(ok)))

print()
print("=== 2. the blocker: 644 ===")
nz = [r for r in ok if re.search(r"644=[1-9]", r["txt"])]
print("  valid runs where 644 ever became nonzero: %d/%d"
      % (len(nz), len(ok)))
byday = defaultdict(lambda: [0, 0])
for r in ok:
    m = re.search(r"_(\d{8})_", r["name"])
    if not m:
        continue
    byday[m.group(1)][1] += 1
    if re.search(r"644=[1-9]", r["txt"]):
        byday[m.group(1)][0] += 1
for d in sorted(byday):
    a, b = byday[d]
    print("    %s : %d/%d" % (d, a, b))

print()
print("=== 3. failure modes (short runs) ===")
for r in R:
    if r["life"] < 60:
        r["_warn"] = "警告码" in r["txt"]
short = [r for r in R if r["life"] < 60]
by = Counter((r["exit"], r["_warn"]) for r in short)
for (ex, w), n in by.most_common():
    print("  exit=%-14s warn=%-6s count=%d" % (ex, w, n))

print()
print("=== 4. does the game ever reach the lobby UI? ===")
n = sum(1 for r in ok if "致命错误" not in r["txt"] and "失去连接" not in r["txt"])
print("  valid runs with NO disconnect dialog: %d/%d" % (n, len(ok)))
