# -*- coding: utf-8 -*-
import os, shutil, io
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
bak = H + ".bak_z7_20261002_2331"
if not os.path.isfile(bak):
    shutil.copy2(H, bak)
    print("BACKUP ->", bak)
else:
    print("BACKUP already exists ->", bak)
with io.open(H, "r", encoding="utf-8", errors="replace") as f:
    txt = f.read()
lines = txt.splitlines()
live = [l for l in lines if l.strip() and not l.strip().startswith("#")]
print("non-comment BEFORE:", len(live))
for l in live: print("  OLD>", l)
# strip any pre-existing codol lines we may have added
lines = [l for l in lines if "codol.qq.com" not in l]
lines.append("")
lines.append("# --- CODOL local lobby (added 2026-10-02) ---")
lines.append("127.0.0.1 formal-zone-auth.codol.qq.com")
lines.append("127.0.0.2 formal-zone-lsg.codol.qq.com")
out = "\r\n".join(lines).rstrip() + "\r\n"
with io.open(H, "w", encoding="utf-8", newline="") as f:
    f.write(out)
with io.open(H, "r", encoding="utf-8", errors="replace") as f:
    txt2 = f.read()
live2 = [l for l in txt2.splitlines() if l.strip() and not l.strip().startswith("#")]
print("non-comment AFTER:", len(live2))
for l in live2: print("  NEW>", l)
