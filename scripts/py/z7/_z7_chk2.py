# -*- coding: utf-8 -*-
import os
LS = os.path.join("CODOLServer","lobby_server","run_2339")
for n in ["auth8443","lsg8444"]:
    p = os.path.join(LS,n+".jsonl")
    print("="*70); print(n)
    if not os.path.isfile(p):
        print("  <missing>"); continue
    d = open(p,"rb").read().decode("utf-8","replace")
    ls = [l for l in d.splitlines() if l.strip()]
    print("  events:", len(ls))
    for l in ls: print("   ", l[:220])
    e = os.path.join(LS,n+".err")
    if os.path.isfile(e) and os.path.getsize(e):
        print("  STDERR:", open(e,"rb").read().decode("utf-8","replace")[-500:])
