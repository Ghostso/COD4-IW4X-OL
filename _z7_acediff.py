"""Good rounds load ace-ats32/tersafe/policyprobe (ACE=3).  Bad rounds load
none (ACE=0) and die at 11-15 s.  Find the FIRST divergence in the module
load sequence.
"""
import os
import re

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
RUNS = os.path.join(ROOT, r"run_codol_001\runs")

GOOD = "IFS1_ELEVATED_20261002_225536"   # life 49.7, ACE=3
BAD = "IFS1_ELEVATED_20261002_230934"    # life 11.6, ACE=0


def load(d):
    p = os.path.join(RUNS, d, "aboprobe.stdout")
    x = open(p, "rb").read().decode("gbk", "replace")
    seq = []
    for l in x.splitlines():
        m = re.match(r"\s*([\d.]+),MODULE,name=([^,]+)", l)
        if m:
            seq.append((float(m.group(1)), m.group(2)))
    return seq


ga = load(GOOD)
gb = load(BAD)

print("good: %d modules   bad: %d modules" % (len(ga), len(gb)))
print()
print("%-34s %-12s %-12s" % ("module", "GOOD t", "BAD t"))

da = {n: t for t, n in ga}
db = {n: t for t, n in gb}

allnames = []
for _, n in ga:
    if n not in allnames:
        allnames.append(n)
for _, n in gb:
    if n not in allnames:
        allnames.append(n)

for n in allnames:
    ta = da.get(n)
    tb = db.get(n)
    if ta is None or tb is None:
        print("%-34s %-12s %-12s   <== MISSING in %s"
              % (n, ta if ta else "-", tb if tb else "-",
                 "BAD" if tb is None else "GOOD"))

print()
print("=== last 6 modules loaded in the BAD round before it died ===")
for t, n in gb[-6:]:
    print("   t=%-8.3f %s" % (t, n))
print()
print("=== what the GOOD round loaded around that same time ===")
cut = gb[-1][0]
for t, n in ga:
    if t <= cut + 2.0:
        print("   t=%-8.3f %s" % (t, n))
