# -*- coding: utf-8 -*-
import os, sys, shutil
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
print("HOSTS =", H)
print("exists:", os.path.isfile(H), "size:", os.path.getsize(H))
with open(H, "rb") as f:
    raw = f.read()
lines = raw.decode("utf-8", "replace").splitlines()
live = [l for l in lines if l.strip() and not l.strip().startswith("#")]
print("total lines:", len(lines), "non-comment:", len(live))
for l in live: print("  LIVE>", l)
try:
    t = open(H, "ab")
    t.close()
    print("WRITABLE: YES")
except Exception as e:
    print("WRITABLE: NO ->", e)
