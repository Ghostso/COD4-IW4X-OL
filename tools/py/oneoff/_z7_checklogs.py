# -*- coding: utf-8 -*-
import os, time
LS = os.path.join("CODOLServer","lobby_server","logs3074b")
for n in ["auth3074b","lsg3074b","auth8443","lsg8444"]:
    p = os.path.join(LS, n + ".jsonl")
    print("="*70); print(n)
    if not os.path.isfile(p):
        print("  <missing>"); continue
    with open(p, "rb") as f:
        data = f.read().decode("utf-8","replace")
    lines = [l for l in data.splitlines() if l.strip()]
    print("  lines:", len(lines))
    for l in lines[-12:]:
        print("   ", l[:200])
