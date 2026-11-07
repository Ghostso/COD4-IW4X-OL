"""What ports did the 09-28 breakthrough actually use, on both sides?"""
import os
import re

D = r"run_codol_001\runs\IFS1_ELEVATED_20260928_183320"

print("=== POKE events in the breakthrough run ===")
f = os.path.join(D, "aboprobe.stdout")
if os.path.exists(f):
    x = open(f, "rb").read().decode("gbk", "replace")
    for l in x.splitlines():
        if "POKE_LOBBY" in l or "COMPLETE" in l:
            print("  ", l.strip()[:200])

print()
print("=== ARGS ===")
lp = os.path.join(D, "launch.txt")
t = open(lp, encoding="utf-8", errors="replace").read()
m = re.search(r"ARGS=(.*)", t)
print("  ", (m.group(1) if m else t)[:500])

print()
print("=== probe logs shipped with that run ===")
for root in ["CODOLServer/logs/PLAIN", "CODOLServer/logs"]:
    if not os.path.isdir(root):
        continue
    for n in sorted(os.listdir(root)):
        if "20260928" in n or "1833" in n:
            p = os.path.join(root, n)
            print("   %-60s %d" % (p, os.path.getsize(p)))
