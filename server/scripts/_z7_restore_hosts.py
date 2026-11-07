# -*- coding: utf-8 -*-
import os, shutil, hashlib, io, subprocess
H = os.path.join(os.environ["windir"],"System32","drivers","etc","hosts")
bak = H + ".bak_z7_20261002_2331"
print("--- hosts ---")
print("  current size:", os.path.getsize(H))
print("  backup  size:", os.path.getsize(bak))
shutil.copy2(bak, H)
print("  RESTORED ->", os.path.getsize(H))
txt = io.open(H,"r",encoding="utf-8",errors="replace").read()
live = [l for l in txt.splitlines() if l.strip() and not l.strip().startswith("#")]
print("  non-comment lines:", len(live))
for l in live: print("    >", l)
