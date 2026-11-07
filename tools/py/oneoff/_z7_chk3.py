# -*- coding: utf-8 -*-
import os
for n in ["auth8443","lsg8444"]:
    p = os.path.join("CODOLServer","lobby_server","run_2339",n+".jsonl")
    print("="*66); print(n)
    ls=[l for l in open(p,"rb").read().decode("utf-8","replace").splitlines() if l.strip()]
    print("  events:", len(ls))
    for l in ls[-20:]: print("   ", l[:200])
