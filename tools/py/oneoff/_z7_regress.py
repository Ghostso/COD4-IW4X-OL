"""Find the last run where 644 succeeded, and what differs from today.

Plain question: the gate used to open (~35-45% of runs on 09-28/09-29).
It is closed now (0% on 09-30, 12% on 10-01, 0% today).  What changed?
"""
import glob
import os
import re
from collections import defaultdict

RUNS = r"run_codol_001\runs"


def load(path):
    x = open(path, "rb").read().decode("gbk", "replace")
    lm = re.search(r"lifetime=([\d.]+)", x)
    life = float(lm.group(1)) if lm else 0.0
    return x, life


rows = []
for d in sorted(glob.glob(os.path.join(RUNS, "IFS1_*")), key=os.path.getmtime):
    f = os.path.join(d, "aboprobe.stdout")
    if not os.path.exists(f):
        continue
    x, life = load(f)
    if life < 60:
        continue
    day = re.search(r"(\d{8})_", os.path.basename(d))
    day = day.group(1) if day else "?"
    good = bool(re.search(r"644=[1-9]", x))
    rows.append({"dir": os.path.basename(d), "day": day, "x": x, "good": good})

good = [r for r in rows if r["good"]]
bad = [r for r in rows if not r["good"]]

print("=== GOOD era (644 reached nonzero) : %d runs ===" % len(good))
for r in good[:3]:
    print("   ", r["dir"])
    for l in r["x"].splitlines():
        if "644=" in l and re.search(r"644=[1-9]", l):
            print("       ", l.strip()[:150])
            break

print()
print("=== BAD era : %d runs ===" % len(bad))
for r in bad[-3:]:
    print("   ", r["dir"])

print()
print("=== event names: good era vs bad era ===")


def events(x):
    return set(re.findall(r",([A-Z0-9_]+),", x))


ge = defaultdict(int)
be = defaultdict(int)
for r in good:
    for e in events(r["x"]):
        ge[e] += 1
for r in bad:
    for e in events(r["x"]):
        be[e] += 1

print("   %-26s %-10s %-10s" % ("event", "good", "bad"))
for n in sorted(set(ge) | set(be)):
    a, b = ge.get(n, 0), be.get(n, 0)
    if (a and not b) or (b and not a):
        tag = "  <== ONLY in good" if a and not b else "  <== ONLY in bad"
        print("   %-26s %-10s %-10s%s" % (n, a, b, tag))
